# app/services/speaking_metrics.py
import math, json

def speaking_metrics_from_utterances(utterances):
    """
    utterances: [{speaker, start, end, text, ...}]
    return: dict をJSON保存推奨
    """
    by_spk = {}
    gaps = []  # ターン間無音
    prev_end = None
    prev_speaker = None
    interruptions = 0

    for u in utterances:
        spk = str(u.get("speaker", "spk"))
        start = float(u.get("start", 0))
        end = float(u.get("end", start))
        text = u.get("text","")
        dur = max(0.0, end - start)

        d = by_spk.setdefault(spk, {"turns":0, "time":0.0, "chars":0})
        d["turns"] += 1
        d["time"]  += dur
        d["chars"] += len(text)

        if prev_end is not None:
            gap = max(0.0, start - prev_end)
            gaps.append(gap)
            # 発話切替かつ隙間が極小なら「割り込み」推定（閾値は要調整）
            if prev_speaker is not None and spk != prev_speaker and gap < 0.25:
                interruptions += 1

        prev_end = end
        prev_speaker = spk

    total_time = sum(d["time"] for d in by_spk.values()) or 1.0
    for spk, d in by_spk.items():
        minutes = max(1e-9, d["time"]/60.0)
        d["cpm"] = d["chars"]/minutes   # 日本語はCPMが安定
        d["ratio"] = d["time"]/total_time
        d["avg_turn_sec"] = d["time"]/max(1, d["turns"])

    metrics = {
        "speakers": by_spk,
        "total_time_sec": total_time,
        "avg_silence_sec": sum(gaps)/len(gaps) if gaps else 0.0,
        "interruptions": interruptions,
    }
    return metrics