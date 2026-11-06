import sys
import json

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

data = json.load(open('benchmark_execution_report.json', encoding='utf-8'))
print(f"{'Test ID':14} | {'Total':>8} | {'TTFT':>8} | {'Emb':>7} | {'Retr':>7} | {'LLM Gen':>8} | {'Top-1 Book':28} | {'Score':>6} | {'Escalation':10} | {'Scholar':22} | {'Book Rec':25}")
print("-" * 165)
for d in data:
    tid = d['test_id']
    t = d['timing']
    top1 = d['retrieval']['candidates'][0] if d['retrieval']['candidates'] else {}
    esc = d['decisions']['suggest_scholar_escalation']
    sch = str(d['decisions']['recommended_scholar'])
    bk = str(d['decisions']['recommended_book'])
    bt = str(top1.get('bookTitle', 'None'))[:26]
    sc = top1.get('score', 0.0)
    print(f"{tid:14} | {t['total_ms']:7.0f}ms | {t['ttft_ms']:7.0f}ms | {t['embedding_ms']:6.0f}ms | {t['retrieval_ms']:6.0f}ms | {t['llm_generation_ms']:7.0f}ms | {bt:28} | {sc:6.3f} | {str(esc):10} | {sch[:20]:22} | {bk[:23]:25}")
