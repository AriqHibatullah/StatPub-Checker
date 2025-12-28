from __future__ import annotations
import os, time
from collections import Counter
from typing import Dict, Set, List, Tuple, Any, Optional

from docx import Document
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

from spellchecker.settings import Settings
from spellchecker.types import Finding

from spellchecker.engine.suggest_wrapper import build_engine, suggest as suggest_call
from spellchecker.extractors.pdf_extractor import iter_pdf_pages_raw

from spellchecker.rules.text import tokenize_with_context, tokenize_docx_paragraph_with_context, normalize_math_text, normalize_text_keep_case
from spellchecker.rules.skip import should_skip_token, is_valid_reduplication, RE_DEGREE_TOKEN
from spellchecker.rules.abbr import paren_abbrev_from_snippet, is_probable_paren_abbrev, is_acronym_like_pdf, is_acronym_like_orig
from spellchecker.rules.citation import should_skip_as_citation_name_pdf, protect_citation_spans_docx
from spellchecker.rules.capital import is_sentence_start_from_offset, is_capitalization_error
from spellchecker.rules.docx_roles import is_role_header_paragraph, protect_name_run_in_paragraph
from spellchecker.rules.names import protect_name_degree_spans
from spellchecker.rules.hyphen import fix_hyphenation_block_with_vocab, protect_hyphen_join_spans_docx, HYPHENS
from spellchecker.rules.team import is_tim_penyusun_page, drop_name_degree_lines, RE_DAFTAR_PUSTAKA, RE_TIM_PENYUSUN, RE_KATA_PENGANTAR
from spellchecker.rules.biblio import is_bibliography_citation_line
from spellchecker.rules.formula import looks_like_formula_line, RE_VAR_DEF
from spellchecker.rules.lang import looks_englishish
from spellchecker.rules.inflection import is_probably_valid_inflection
from spellchecker.rules.glossary import is_doc_term_candidate, is_strong_typo_from_suggestions
from spellchecker.rules.context_skip import should_skip_address_token, should_skip_paren_author_verb, should_skip_author_year
from spellchecker.morph.space_nya import detect_space_error_nya
from spellchecker.morph.affix import (
    maybe_affixed_id, cached_stem, deaffix_for_suggest,
    pick_best_suggest_query_for_nya, reaffix_suggestion,
    top1_conf, is_synth_top, top_term, apply_luluh_candidates
)

def build_vocabs(
    kbbi: Set[str],
    kamus_id: Set[str],
    domain_terms: Set[str],
    kamus_en: Set[str],
    singkatan: Set[str],
    ignore_vocab: Set[str],
) -> Tuple[Set[str], Set[str], Set[str]]:
    known_vocab = set(kbbi) | set(kamus_id) | set(domain_terms)
    english_vocab = set(kamus_en) | set(singkatan)
    known_vocab_for_names = known_vocab | english_vocab | set(ignore_vocab)
    return known_vocab, english_vocab, known_vocab_for_names

def run_on_file(
    path: str,
    cfg: Settings,
    known_vocab: Set[str],
    english_vocab: Set[str],
    known_vocab_for_names: Set[str],
    ignore_vocab: Set[str],
    domain_terms: Set[str],
    protected_phrases: Set[str],
    protected_name_tokens: Set[str],
) -> Tuple[List[Finding], Dict[str, Any]]:
    base = os.path.basename(path)
    eng = build_engine(resources, models)
    stemmer = StemmerFactory().create_stemmer()

    findings: List[Finding] = []
    doc_term_counter = Counter()
    doc_glossary: Set[str] = set()
    glossary_candidates: Set[str] = set()

    abbr_seen: Set[str] = set()
    abbr_reported: Set[str] = set()
    abbr_candidate_count = Counter()
    unknown_seen: Set[str] = set()

    morph_log: List[Tuple[str, str]] = []
    stem_cache: Dict[str, str] = {}
    doc_symbols: Set[str] = set()

    count_file = 0

    if path.lower().endswith(".pdf"):
        crew_pages_left = 0
        for page_no, page_text in iter_pdf_pages_raw(path):
            is_crew = False
            if cfg.enable_tim_penyusun_filter and page_no <= cfg.tim_page_limit:
                if is_tim_penyusun_page(page_text):
                    crew_pages_left = cfg.crew_pages_span
                if crew_pages_left > 0:
                    is_crew = True
                    crew_pages_left -= 1

            if is_crew:
                page_text = drop_name_degree_lines(page_text)

            # NOTE: keep it simple here; you can port your full "filtered_lines" logic if needed
            for line in (page_text or "").splitlines():
                line = (line or "").strip()
                if not line:
                    continue
                if is_bibliography_citation_line(line):
                    continue
                if looks_like_formula_line(line):
                    t_norm = normalize_math_text(line)
                    m = RE_VAR_DEF.match(t_norm)
                    if m:
                        doc_symbols.add(m.group(1).lower())
                    continue
                t_norm = normalize_math_text(line)
                m = RE_VAR_DEF.match(t_norm)
                if m:
                    doc_symbols.add(m.group(1).lower())

            for tok, snippet, snippet_raw in tokenize_with_context(page_text):
                abbr_seen |= paren_abbrev_from_snippet(snippet_raw)

                if tok in doc_symbols:
                    continue

                if is_probable_paren_abbrev(tok, snippet_raw):
                    if tok not in abbr_reported:
                        findings.append(Finding(base, str(page_no), tok, snippet, "abbr_confirmed", []))
                        abbr_reported.add(tok)
                        count_file += 1
                        if count_file >= cfg.max_findings_per_file:
                            break
                    continue

                if tok in abbr_seen:
                    continue

                if is_acronym_like_pdf(tok, snippet_raw) and tok not in abbr_seen:
                    if tok not in known_vocab and tok not in english_vocab and tok not in ignore_vocab:
                        abbr_candidate_count[tok] += 1
                        if abbr_candidate_count[tok] == cfg.abbr_cand_min_count:
                            findings.append(Finding(base, str(page_no), tok, snippet, "abbr_candidate", []))
                            count_file += 1
                            if count_file >= cfg.max_findings_per_file:
                                break
                    continue

                if should_skip_token(tok, cfg):
                    continue
                if RE_DEGREE_TOKEN.match(tok):
                    continue
                if is_valid_reduplication(tok, known_vocab):
                    continue
                if tok in ignore_vocab:
                    continue
                if tok in english_vocab:
                    continue

                if protected_phrases and tok in snippet:
                    if any((tok in ph and ph in snippet) for ph in protected_phrases):
                        continue

                if tok in known_vocab:
                    continue

                if is_probably_valid_inflection(tok, known_vocab, cfg):
                    continue

                if looks_englishish(tok, english_vocab, cfg, snippet):
                    continue

                if tok in protected_name_tokens:
                    continue

                if should_skip_as_citation_name_pdf(tok, snippet, known_vocab, english_vocab, cfg):
                    continue

                # Sastrawi success => skip
                if tok.isalpha() and tok not in known_vocab and tok not in english_vocab and maybe_affixed_id(tok):
                    stem = cached_stem(tok, stemmer, stem_cache)
                    if stem and stem != tok and stem in known_vocab:
                        morph_log.append((tok, stem))
                        continue

                res = suggest_call(eng, tok, cfg.topk)
                suggs = res.get("suggestions", [])
                status = res.get("status", "")

                if is_doc_term_candidate(tok, known_vocab, english_vocab, cfg):
                    doc_term_counter[tok] += 1
                    if (
                        doc_term_counter[tok] >= cfg.auto_glossary_min_freq
                        and len(doc_glossary) < cfg.auto_glossary_max_doc_terms
                        and not is_strong_typo_from_suggestions(suggs, cfg)
                    ):
                        doc_glossary.add(tok)
                        glossary_candidates.add(tok)
                        continue

                if tok in doc_glossary:
                    continue

                if suggs:
                    top1 = suggs[0].get("confidence")
                    if isinstance(top1, (int, float)) and top1 >= cfg.show_only_top1_if_conf_ge:
                        suggs = suggs[:1]

                is_unknownish = (not suggs) or (isinstance(suggs[0].get("confidence"), (int, float)) and suggs[0].get("confidence") < cfg.auto_glossary_conf_strong)
                if is_unknownish and tok in unknown_seen:
                    continue
                if is_unknownish:
                    unknown_seen.add(tok)

                if status == "ok":
                    continue

                findings.append(Finding(base, str(page_no), tok, snippet, status, suggs))
                count_file += 1
                if count_file >= cfg.max_findings_per_file:
                    break

            if count_file >= cfg.max_findings_per_file:
                break

    else:
        doc = Document(path)
        page_label = "DOCX"
        pending_role_header = False
        in_bibliography = False
        in_timpenyusun = False
        carry: Optional[str] = None
        carry_from_hyphen = False

        for p in doc.paragraphs:
            text = (p.text or "").strip()
            if not text:
                continue

            if RE_TIM_PENYUSUN.match(text):
                in_timpenyusun = True
                continue
            if RE_KATA_PENGANTAR.match(text):
                in_timpenyusun = False
                continue
            if in_timpenyusun:
                continue

            if RE_DAFTAR_PUSTAKA.match(text):
                in_bibliography = True
                continue
            if in_bibliography:
                continue

            if is_role_header_paragraph(text):
                pending_role_header = True
                continue

            if looks_like_formula_line(text):
                t_norm = normalize_math_text(text)
                m = RE_VAR_DEF.match(t_norm)
                if m:
                    doc_symbols.add(m.group(1).lower())
                continue

            t_norm = normalize_math_text(text)
            m = RE_VAR_DEF.match(t_norm)
            if m:
                doc_symbols.add(m.group(1).lower())

            if is_bibliography_citation_line(text):
                continue

            fixed_text = fix_hyphenation_block_with_vocab(p.text or "", known_vocab_for_names)

            triples = tokenize_docx_paragraph_with_context(fixed_text)
            if not triples:
                continue

            toks_norm = [t[0] for t in triples]
            toks_orig = [t[1] for t in triples]
            raw_para = normalize_text_keep_case(text)

            skip_first = False
            if carry is not None:
                first = toks_norm[0]
                if carry.isalpha() and first.isalpha():
                    joined = carry + first
                    if joined in known_vocab_for_names:
                        skip_first = True
                carry = None
                carry_from_hyphen = False

            extra_protect: Set[int] = set()
            if pending_role_header:
                extra_protect |= protect_name_run_in_paragraph(
                    triples,
                    known_vocab=known_vocab_for_names,
                    english_vocab=english_vocab,
                    cfg=cfg,
                    min_titlecase=2,
                    max_take=8,
                )
                pending_role_header = False

            protected_idx = protect_name_degree_spans(toks_norm, toks_orig, known_vocab_for_names, cfg)
            protected_idx |= protect_citation_spans_docx(toks_norm, toks_orig, cfg)
            protected_idx |= extra_protect
            protected_idx |= protect_hyphen_join_spans_docx(triples, known_vocab_for_names)

            # carry last token heuristic
            hold_last_as_carry = False
            last_idx = len(toks_norm) - 1
            last_tok = toks_norm[last_idx]
            last_orig = toks_orig[last_idx] if last_idx < len(toks_orig) else ""
            ends_with_hyphen = last_orig.endswith(HYPHENS)

            if ends_with_hyphen:
                prefix = last_orig
                import re as _re
                prefix = _re.sub(r"[-‐-]+$", "", prefix).strip().lower()
                if prefix.isalpha():
                    hold_last_as_carry = True
                    carry = prefix
                    carry_from_hyphen = True
            else:
                if last_tok.isalpha() and 1 <= len(last_tok) <= 3 and last_tok not in known_vocab_for_names:
                    hold_last_as_carry = True
                    carry = last_tok
                    carry_from_hyphen = False

            if skip_first:
                protected_idx.add(0)

            for idx, (tok, tok_orig, snippet, snippet_raw, t_start, t_end) in enumerate(triples):
                if idx in protected_idx:
                    continue
                if tok in doc_symbols:
                    continue
                
                nya_info = detect_space_error_nya(triples, idx)
                if nya_info is not None:
                    join_term = nya_info["join_term"]
                    findings.append(Finding(
                        file=base,
                        page=page_label,
                        token=tok,
                        snippet=snippet,
                        status="space_error",
                        suggestions=[{"term": join_term, "confidence": 1.0}],
                    ))
                    count_file += 1
                    if count_file >= cfg.max_findings_per_file:
                        break
                    continue

                if hold_last_as_carry and idx == last_idx:
                    continue

                if should_skip_token(tok, cfg):
                    continue
                if RE_DEGREE_TOKEN.match(tok):
                    continue
                if should_skip_address_token(tok, snippet_raw):
                    continue
                if should_skip_paren_author_verb(tok, snippet_raw):
                    continue
                if should_skip_author_year(tok, snippet_raw):
                    continue

                if tok in domain_terms or tok in protected_phrases:
                    continue
                if tok in ignore_vocab:
                    continue

                # capital
                is_start = is_sentence_start_from_offset(raw_para, t_start)
                if is_start and is_capitalization_error(tok_orig):
                    sugg = tok_orig[:1].upper() + tok_orig[1:]
                    findings.append(Finding(
                        file=base,
                        page=page_label,
                        token=tok,
                        snippet=snippet_raw,
                        status="capital_error",
                        suggestions=[{"term": sugg, "confidence": 1.0}],
                    ))
                    count_file += 1
                    if count_file >= cfg.max_findings_per_file:
                        break
                    continue

                if is_valid_reduplication(tok, known_vocab_for_names):
                    continue
                if tok in known_vocab_for_names:
                    continue

                # abbreviations
                abbr_seen |= paren_abbrev_from_snippet(snippet_raw)
                if is_probable_paren_abbrev(tok, snippet_raw):
                    if tok not in abbr_reported:
                        findings.append(Finding(base, page_label, tok, snippet_raw, "abbr_confirmed", []))
                        abbr_reported.add(tok)
                        count_file += 1
                        if count_file >= cfg.max_findings_per_file:
                            break
                    continue
                if tok in abbr_seen:
                    continue
                
                if is_acronym_like_orig(tok_orig) and tok not in abbr_seen:
                    if tok not in known_vocab and tok not in english_vocab and tok not in ignore_vocab:
                        abbr_candidate_count[tok] += 1
                        if abbr_candidate_count[tok] == cfg.abbr_cand_min_count:
                            findings.append(Finding(base, page_label, tok, snippet_raw, "abbr_candidate", []))
                            count_file += 1
                            if count_file >= cfg.max_findings_per_file:
                                break
                    continue

                if is_probably_valid_inflection(tok, known_vocab, cfg):
                    continue
                if looks_englishish(tok, english_vocab, cfg, snippet):
                    continue
                if tok in protected_name_tokens:
                    continue

                # -------- suggestion: raw first (confusion short-circuit) ----------
                raw_res = suggest_call(eng, tok, cfg.topk)
                raw_suggs = raw_res.get("suggestions", [])
                raw_status = raw_res.get("status", "")

                if raw_status == "confusion":
                    res = raw_res
                    suggs = raw_suggs
                    status = raw_status
                    affix_info = None
                    suggest_query = tok
                    goto_after_affix = True
                else:
                    goto_after_affix = False

                suggest_query = tok
                affix_info = None
                if not tok_orig[:1].isupper():
                    if tok.isalpha() and tok not in known_vocab and tok not in english_vocab and maybe_affixed_id(tok):
                        stem = cached_stem(tok, stemmer, stem_cache)

                        if stem and stem != tok and stem in known_vocab:
                            morph_log.append((tok, stem))
                            continue

                        if stem == tok:
                            base_tok, info = deaffix_for_suggest(tok)
                            if base_tok != tok and len(base_tok) >= 3:
                                cands = apply_luluh_candidates(base_tok, info.get("prefixes", []))

                                picked = None
                                for c in cands:
                                    if c in known_vocab:
                                        picked = c
                                        break

                                if picked is not None:
                                    base_tok = picked
                                else:
                                    best = cands[0]
                                    best_res = eng.suggest(best, topk=cfg.topk)
                                    best_conf = top1_conf(best_res.get("suggestions", []))

                                    for c in cands[1:]:
                                        res = eng.suggest(c, topk=cfg.topk)
                                        conf = top1_conf(res.get("suggestions", []))
                                        if conf > best_conf:
                                            best, best_res, best_conf = c, res, conf

                                    base_tok = best

                                suggest_query = base_tok
                                affix_info = info

                used_prefetch_res = None
                if affix_info and affix_info.get("suffixes") and affix_info["suffixes"][0] == "nya":
                    suggest_query, used_prefetch_res = pick_best_suggest_query_for_nya(tok, eng, cfg.topk, suggest_call)

                if used_prefetch_res is not None:
                    res = used_prefetch_res
                else:
                    res = suggest_call(eng, suggest_query, cfg.topk)

                suggs = res.get("suggestions", [])
                status = res.get("status", "")

                if not goto_after_affix:
                    if affix_info is not None and suggest_query != tok:
                        status = cfg.status_affix_typo
                        if not suggs:
                            suggs = [{"suggestion": suggest_query, "term": suggest_query, "confidence": 0.01, "_synthetic": True}]

                    if affix_info and suggs:
                        re_sugs = []
                        for s in suggs:
                            cand = s.get("term") or s.get("suggestion") or s.get("word")
                            if not cand:
                                continue
                            new_s = dict(s)
                            new_term = reaffix_suggestion(cand, affix_info)
                            new_s["term"] = new_term
                            new_s["suggestion"] = new_term
                            re_sugs.append(new_s)
                        suggs = re_sugs

                    # pick raw vs affix
                    final_suggs = raw_suggs
                    final_status = raw_status

                    raw_conf = top1_conf(raw_suggs)
                    aff_conf = top1_conf(suggs)

                    use_affix = (affix_info is not None and suggest_query != tok)

                    if use_affix:
                        if raw_conf >= cfg.auto_glossary_conf_strong:
                            use_affix = False

                        if use_affix and is_synth_top(suggs):
                            top = (suggs[0].get("term") or suggs[0].get("suggestion") or "").lower()
                            if top and top not in known_vocab:
                                use_affix = False

                        short_pfx = {"di", "ke", "se", "pe"}
                        if use_affix and any(p in short_pfx for p in (affix_info or {}).get("prefixes", [])):
                            top = (suggs[0].get("term") or suggs[0].get("suggestion") or "").lower()
                            if top and top not in known_vocab:
                                use_affix = False

                        if use_affix and aff_conf <= raw_conf + 0.12:
                            use_affix = False

                    if use_affix:
                        final_suggs = suggs
                        final_status = status

                    suggs = final_suggs
                    status = final_status

                # auto glossary (only on raw token)
                if affix_info is None and is_doc_term_candidate(tok, known_vocab, english_vocab, cfg):
                    doc_term_counter[tok] += 1
                    if (
                        doc_term_counter[tok] >= cfg.auto_glossary_min_freq
                        and len(doc_glossary) < cfg.auto_glossary_max_doc_terms
                        and not is_strong_typo_from_suggestions(suggs, cfg)
                    ):
                        doc_glossary.add(tok)
                        glossary_candidates.add(tok)
                        continue

                if tok in doc_glossary:
                    continue

                if suggs:
                    top1 = suggs[0].get("confidence")
                    if isinstance(top1, (int, float)) and top1 >= cfg.show_only_top1_if_conf_ge:
                        suggs = suggs[:1]

                is_unknownish = (not suggs) or (isinstance(suggs[0].get("confidence"), (int, float)) and suggs[0].get("confidence") < cfg.auto_glossary_conf_strong)
                if is_unknownish and tok in unknown_seen:
                    continue
                if is_unknownish:
                    unknown_seen.add(tok)

                if status == "ok":
                    continue

                findings.append(Finding(base, page_label, tok, snippet_raw, status, suggs))
                count_file += 1
                if count_file >= cfg.max_findings_per_file:
                    break

            if count_file >= cfg.max_findings_per_file:
                break

    meta = {
        "file": base,
        "created_at": time.strftime("%Y-%m-%d"),
        "topk": cfg.topk,
        "findings_count": len(findings),
        "morph_ok_count": len(morph_log),
        "glossary_candidates_count": len(glossary_candidates),
    }
    return findings, meta
