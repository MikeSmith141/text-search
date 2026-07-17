#!/usr/bin/env python3
"""古籍自动标点（CPU批量优化版）"""
import argparse
import re
import sys
import time
from pathlib import Path

MODEL_ID = "raynardj/classical-chinese-punctuation-guwen-biaodian"


def needs_punct(text: str, min_count: int = 80) -> bool:
    return len(re.findall(r"[，。！？；：、]", text)) < min_count


def load_model():
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    import torch
    print(f"loading {MODEL_ID} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_ID)
    model.eval()
    print("ready", flush=True)
    return tok, model, model.config.id2label


def punctuate_chunk(tok, model, id2label, chunk: str) -> str:
    import torch
    if not chunk:
        return ""
    enc = tok(list(chunk), is_split_into_words=True, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**enc).logits[0]
    pred = logits.argmax(dim=-1).tolist()
    word_ids = enc.word_ids(batch_index=0)
    labels = []
    seen = set()
    for wi, lab_id in zip(word_ids, pred):
        if wi is None or wi in seen:
            continue
        seen.add(wi)
        labels.append(str(id2label[lab_id]).replace("B-", "").replace("I-", ""))
    out = []
    for ch, lab in zip(chunk, labels):
        out.append(ch)
        if lab in list("，。！？；：、\"“”‘’"):
            out.append(lab)
    return "".join(out)


def process_file(tok, model, id2label, path: Path, force=False, win=240):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not force and not needs_punct(raw):
        print(f"skip {path.name}", flush=True)
        return

    # 保留开头来源说明
    header_lines = []
    body_lines = raw.splitlines()
    while body_lines and (body_lines[0].startswith("（") or body_lines[0].startswith("【") and "来源" in body_lines[0] or not body_lines[0].strip()):
        if body_lines[0].strip():
            header_lines.append(body_lines[0].strip())
        body_lines.pop(0)
        if len(header_lines) >= 3:
            break

    plain = re.sub(r"[，。！？；：、\"“”‘’＇\s]", "", "\n".join(body_lines))
    print(f"punctuating {path.name}: plain_chars={len(plain)} win={win}", flush=True)
    t0 = time.time()
    parts = []
    n = len(plain)
    for i in range(0, n, win):
        chunk = plain[i:i + win]
        parts.append(punctuate_chunk(tok, model, id2label, chunk))
        done = min(i + win, n)
        if done % (win * 20) < win or done == n:
            print(f"  {path.name}: {done*100//n}% ({done}/{n}) {time.time()-t0:.1f}s", flush=True)

    text = "".join(parts)
    # 粗分段：句号后换行
    text = re.sub(r"([。？！])", r"\1\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    head = "（本文件由模型自动标点：raynardj/classical-chinese-punctuation-guwen-biaodian；请以原典复核）\n"
    if header_lines:
        head += "\n".join(header_lines) + "\n"
    path.write_text(head + "\n" + text, encoding="utf-8")
    punct = len(re.findall(r"[，。！？；：、]", text))
    print(f"done {path.name}: punct={punct} chars={len(text)} time={time.time()-t0:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dir", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--win", type=int, default=240)
    args = ap.parse_args()
    files = [Path(p) for p in args.paths]
    if args.dir:
        files += sorted(Path(args.dir).glob("*.txt"))
    if not files:
        print("no files"); return 1
    if not args.paths and not args.force:
        files = [f for f in files if needs_punct(f.read_text(encoding="utf-8", errors="replace"))]
    print("targets:", [f.name for f in files], flush=True)
    tok, model, id2label = load_model()
    for f in files:
        try:
            process_file(tok, model, id2label, f, force=args.force or bool(args.paths), win=args.win)
        except Exception as e:
            print("ERROR", f, e, flush=True)
            import traceback; traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main())
