"""Tugas 4 Kriptografi — Praktikum Steganografi.
Jalankan: python3 src/praktikum_steganografi.py
"""
from __future__ import annotations

from pathlib import Path
import json
import math
import textwrap

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COVER = ROOT / "cover_farid.png"
OUT = ROOT / "output"
SCREENSHOTS = ROOT / "screenshots"
NIM = 237006081
WRONG_SEED = NIM + 1
ENCRYPTION_SEED = 173006081
MESSAGE = (
    "237006081 - Farid Firdaus - Saya mempelajari steganografi digital "
    "untuk melindungi pesan rahasia secara hati-hati."
)


def bits_from_bytes(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bytes_from_bits(bits: np.ndarray) -> bytes:
    usable = len(bits) - (len(bits) % 8)
    return np.packbits(bits[:usable]).tobytes()


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()


def save_rgb(array: np.ndarray, path: Path, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Array selalu (H, W, 3) uint8, sehingga mode RGB dideteksi otomatis.
    # Argumen mode eksplisit ("RGB") sudah deprecated pada Pillow 13.
    Image.fromarray(array).save(path, **kwargs)


def psnr_and_mse(cover: np.ndarray, stego: np.ndarray) -> tuple[float, float]:
    mse = float(np.mean((cover.astype(np.float64) - stego.astype(np.float64)) ** 2))
    return mse, float("inf") if mse == 0 else 10 * math.log10(255**2 / mse)


def capacity_bits(image: np.ndarray, m: int = 1) -> int:
    return int(image.size * m)


def embed_sequential(image: np.ndarray, payload: bytes, m: int = 1, header: bool = True) -> np.ndarray:
    if not 1 <= m <= 4:
        raise ValueError("m must be 1..4")
    payload_bits = bits_from_bytes(payload)
    bits = np.concatenate((np.array([(len(payload_bits) >> i) & 1 for i in range(31, -1, -1)], dtype=np.uint8), payload_bits)) if header else payload_bits
    if len(bits) > capacity_bits(image, m):
        raise ValueError("payload exceeds image capacity")
    flat = image.reshape(-1).copy()
    mask = (1 << m) - 1
    padded = np.pad(bits, (0, (-len(bits)) % m))
    values = padded.reshape(-1, m).dot(1 << np.arange(m - 1, -1, -1))
    flat[:len(values)] = (flat[:len(values)] & np.uint8(0xFF ^ mask)) | values.astype(np.uint8)
    return flat.reshape(image.shape)


def extract_sequential_bits(image: np.ndarray, bit_count: int, m: int = 1, offset_bits: int = 0) -> np.ndarray:
    flat = image.reshape(-1)
    mask = (1 << m) - 1
    all_bits = np.unpackbits((flat & mask).astype(np.uint8))
    # np.unpackbits gives 8 bits; retain last m bits per byte.
    all_bits = all_bits.reshape(-1, 8)[:, -m:].reshape(-1)
    return all_bits[offset_bits:offset_bits + bit_count]


def extract_sequential(image: np.ndarray, m: int = 1) -> tuple[bytes | None, str]:
    header = extract_sequential_bits(image, 32, m)
    if len(header) != 32:
        return None, "gagal: header 32-bit tidak tersedia"
    declared = int("".join(map(str, header)), 2)
    available = capacity_bits(image, m) - 32
    if declared < 0 or declared > available or declared % 8:
        return None, f"gagal: header panjang tidak valid ({declared} bit)"
    return bytes_from_bits(extract_sequential_bits(image, declared, m, 32)), "berhasil"


def positions_for(image: np.ndarray, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).permutation(image.size)


def embed_random(image: np.ndarray, payload: bytes, seed: int) -> np.ndarray:
    payload_bits = bits_from_bytes(payload)
    bits = np.concatenate((np.array([(len(payload_bits) >> i) & 1 for i in range(31, -1, -1)], dtype=np.uint8), payload_bits))
    if len(bits) > image.size:
        raise ValueError("payload exceeds image capacity")
    flat = image.reshape(-1).copy()
    positions = positions_for(image, seed)[:len(bits)]
    flat[positions] = (flat[positions] & 0xFE) | bits
    return flat.reshape(image.shape)


def extract_random(image: np.ndarray, seed: int) -> tuple[bytes | None, str]:
    flat = image.reshape(-1)
    positions = positions_for(image, seed)
    header_bits = flat[positions[:32]] & 1
    declared = int("".join(map(str, header_bits)), 2)
    available = image.size - 32
    if declared > available or declared % 8:
        return None, f"gagal: header panjang tidak valid ({declared} bit)"
    payload_bits = flat[positions[32:32 + declared]] & 1
    return bytes_from_bits(payload_bits), "berhasil"


def xor_keystream(data: bytes, seed: int) -> bytes:
    stream = np.random.default_rng(seed).integers(0, 256, len(data), dtype=np.uint8)
    return (np.frombuffer(data, dtype=np.uint8) ^ stream).tobytes()


def bit_error_rate(expected: np.ndarray, actual: np.ndarray) -> float:
    if len(expected) != len(actual):
        raise ValueError("bit arrays have different lengths")
    return float(np.mean(expected != actual) * 100)


def change_map(cover: np.ndarray, stego: np.ndarray) -> np.ndarray:
    changed = np.any(cover != stego, axis=2)
    return np.where(changed[..., None], 255, 0).astype(np.uint8).repeat(3, axis=2)


def console_image(lines: list[str], path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(14, max(4, 0.36 * len(lines) + 1.5)), dpi=150)
    fig.patch.set_facecolor("#101418")
    ax.set_facecolor("#101418")
    ax.axis("off")
    ax.text(0.03, 0.96, title, va="top", family="monospace", fontsize=11, color="#e6edf3")
    ax.text(0.03, 0.88, "\n".join(lines), va="top", family="monospace", fontsize=9.5, color="#b8f7c4", linespacing=1.35)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


# Reproduksi logika slide untuk P1. Sengaja mempertahankan dua masalah slide:
# range(0, 2) hanya memakai R,G; bin(x)[2:9] tidak memberi padding 8-bit.
def slide_embedding_baseline(image: np.ndarray, message: str) -> np.ndarray:
    payload = (message + "stego").encode("utf-8")
    bits = "".join(format(byte, "08b") for byte in payload)
    pixels = image.reshape(-1, 3).copy()
    index = 0
    for p in range(len(pixels)):
        for q in range(0, 2):
            if index < len(bits):
                pixels[p][q] = int(bin(int(pixels[p][q]))[2:9] + bits[index], 2)
                index += 1
    return pixels.reshape(image.shape)


def slide_extract_baseline(image: np.ndarray) -> str:
    pixels = image.reshape(-1, 3)
    bit_message = ""
    for p in range(len(pixels)):
        for q in range(0, 2):
            bit_message += bin(int(pixels[p][q]))[-1]
    chars = [bit_message[i:i + 8] for i in range(0, len(bit_message), 8)]
    message = ""
    for char_bits in chars:
        if message[-5:] == "stego":
            break
        message += chr(int(char_bits, 2))
    return message[:-5] if "stego" in message else "Tidak ada pesan tersembunyi di dalam citra"


def slide_synthetic_low_value_proof(message: str) -> dict:
    """Bukti sintetis kecil bahwa bug bin(x)[2:9] benar-benar terpicu.

    Citra ini sengaja bernilai rendah (< 128) supaya setiap kanal tidak
    memiliki 8 bit penuh. Akibatnya bin(x)[2:9] memotong bit dan menyisipkan
    LSB pada posisi bergeser, sehingga selisih channel-byte bisa > 1. Pada
    citra asli (cover foto) hampir semua kanal >= 128, sehingga bug sering
    tersamarkan dan selisih maksimum tampak = 1.
    """
    low_values = np.array([3, 5, 6, 7, 9, 11], dtype=np.uint8)
    synthetic = np.resize(low_values, (6, 6, 3)).astype(np.uint8).copy()
    baseline = slide_embedding_baseline(synthetic, message)
    fixed = embed_sequential(synthetic, message.encode("utf-8"), 1)
    baseline_diff = np.abs(synthetic.astype(int) - baseline.astype(int))
    fixed_diff = np.abs(synthetic.astype(int) - fixed.astype(int))
    return {
        "synthetic": synthetic,
        "baseline": baseline,
        "shape": list(synthetic.shape),
        "low_values": low_values.tolist(),
        "baseline_max_difference": int(baseline_diff.max()),
        "baseline_changed_bytes": int(np.count_nonzero(synthetic != baseline)),
        "fixed_max_difference": int(fixed_diff.max()),
        "fixed_changed_bytes": int(np.count_nonzero(synthetic != fixed)),
        "total_channel_bytes": int(synthetic.size),
    }


def run_p1(cover: np.ndarray, payload: bytes, results: dict) -> None:
    p = OUT / "p1"
    baseline = slide_embedding_baseline(cover, MESSAGE)
    save_rgb(baseline, p / "stego_slide_baseline.png")
    baseline_diff = np.abs(cover.astype(int) - baseline.astype(int))
    baseline_text = slide_extract_baseline(baseline)
    fixed = embed_sequential(cover, payload, 1)
    save_rgb(fixed, p / "stego_p1_fixed_header32.png")
    extracted, fixed_status = extract_sequential(fixed, 1)
    fixed_diff = np.abs(cover.astype(int) - fixed.astype(int))
    synthetic = slide_synthetic_low_value_proof("P1")
    save_rgb(synthetic["baseline"], p / "stego_slide_synthetic_low_value.png")
    lines = [
        "P1 — Reproduksi dan perbaikan program slide",
        f"Pesan: {MESSAGE}",
        f"Baseline slide ekstraksi: {baseline_text}",
        "Catatan: selisih di bawah diukur per channel-byte (R/G/B), bukan per piksel.",
        f"Baseline (citra asli) selisih channel-byte maksimum: {baseline_diff.max()}",
        f"Baseline (citra asli) channel-byte berubah: {np.count_nonzero(cover != baseline)}",
        "Penyebab: bin(x)[2:9] tidak zero-pad 8-bit; nilai kecil dapat berubah > 1.",
        "Penyebab kapasitas: range(0, 2) hanya memakai kanal R dan G.",
        "Bukti sintetis nilai rendah (kanal < 128) agar bug benar-benar terpicu:",
        f"  Nilai kanal uji: {synthetic['low_values']} | ukuran: {synthetic['shape']}",
        f"  Bukti sintetis baseline selisih channel-byte maksimum: {synthetic['baseline_max_difference']}",
        f"  Bukti sintetis baseline channel-byte berubah: {synthetic['baseline_changed_bytes']} / {synthetic['total_channel_bytes']}",
        f"  Bukti sintetis perbaikan selisih channel-byte maksimum: {synthetic['fixed_max_difference']}",
        f"  Bukti sintetis perbaikan channel-byte berubah: {synthetic['fixed_changed_bytes']} / {synthetic['total_channel_bytes']}",
        "Perbaikan: operasi bitwise (value & 0xFE) | bit, semua kanal RGB.",
        "Perbaikan akhir pesan: header panjang 32-bit, bukan delimiter 'stego'.",
        f"Stego perbaikan ekstraksi: {extracted.decode('utf-8') if extracted else None}",
        f"Status: {fixed_status}",
        f"Perbaikan (citra asli) selisih channel-byte maksimum: {fixed_diff.max()} (teori 1-bit LSB: 1)",
        f"Perbaikan (citra asli) channel-byte berubah: {np.count_nonzero(cover != fixed)}",
        f"Kapasitas slide (R,G): {cover.shape[0] * cover.shape[1] * 2} bit",
        f"Kapasitas teoretis/perbaikan (R,G,B): {cover.size} bit",
    ]
    console_image(lines, SCREENSHOTS / "p1_console.png", "Output P1")
    results["p1"] = {
        "difference_unit": "channel-byte",
        "baseline_max_difference": int(baseline_diff.max()),
        "baseline_changed_bytes": int(np.count_nonzero(cover != baseline)),
        "fixed_max_difference": int(fixed_diff.max()),
        "fixed_changed_bytes": int(np.count_nonzero(cover != fixed)),
        "synthetic_low_value": {
            "shape": synthetic["shape"],
            "low_values": synthetic["low_values"],
            "total_channel_bytes": synthetic["total_channel_bytes"],
            "baseline_max_difference": synthetic["baseline_max_difference"],
            "baseline_changed_bytes": synthetic["baseline_changed_bytes"],
            "fixed_max_difference": synthetic["fixed_max_difference"],
            "fixed_changed_bytes": synthetic["fixed_changed_bytes"],
        },
        "slide_capacity_bits": int(cover.shape[0] * cover.shape[1] * 2),
        "theoretical_capacity_bits": int(cover.size),
        "fixed_extraction": extracted.decode("utf-8") if extracted else None,
    }


def run_p2(cover: np.ndarray, payload: bytes, results: dict) -> None:
    p = OUT / "p2"
    sequential = embed_sequential(cover, payload)
    random = embed_random(cover, payload, NIM)
    save_rgb(sequential, p / "stego_sequential.png")
    save_rgb(random, p / "stego_random_seed_237006081.png")
    save_rgb(change_map(cover, sequential), p / "change_map_sequential.png")
    save_rgb(change_map(cover, random), p / "change_map_random.png")
    good, good_status = extract_random(random, NIM)
    wrong, wrong_status = extract_random(random, WRONG_SEED)
    lines = [
        "P2 — LSB acak dengan stego-key",
        f"Seed benar: {NIM}",
        f"Hasil seed benar: {good.decode('utf-8') if good else None}",
        f"Status seed benar: {good_status}",
        f"Seed salah: {WRONG_SEED}",
        f"Hasil seed salah: {wrong.decode('utf-8', errors='replace') if wrong else None}",
        f"Status seed salah: {wrong_status}",
        f"Byte berubah sequential: {np.count_nonzero(cover != sequential)}",
        f"Byte berubah random: {np.count_nonzero(cover != random)}",
    ]
    console_image(lines, SCREENSHOTS / "p2_console.png", "Output P2")
    results["p2"] = {
        "correct_seed_status": good_status,
        "correct_seed_extraction": good.decode("utf-8") if good else None,
        "wrong_seed_status": wrong_status,
        "sequential_changed_bytes": int(np.count_nonzero(cover != sequential)),
        "random_changed_bytes": int(np.count_nonzero(cover != random)),
    }


def run_p3(cover: np.ndarray, results: dict) -> None:
    p = OUT / "p3"
    rows = []
    rng = np.random.default_rng(NIM)
    previews = []
    for m in range(1, 5):
        # Full capacity uses all channel bytes; require a bit count divisible by m and 8.
        usable_bits = capacity_bits(cover, m) - (capacity_bits(cover, m) % 8)
        random_payload = rng.integers(0, 256, usable_bits // 8, dtype=np.uint8).tobytes()
        stego = embed_sequential(cover, random_payload, m, header=False)
        save_rgb(stego, p / f"stego_m{m}_full_capacity.png")
        mse, psnr = psnr_and_mse(cover, stego)
        rows.append({"m": m, "capacity_bits": usable_bits, "capacity_kb": usable_bits / 8 / 1024, "mse": mse, "psnr_db": psnr})
        previews.append(stego)
    fig, ax = plt.subplots(figsize=(8, 5), dpi=180)
    ax.plot([row["m"] for row in rows], [row["psnr_db"] for row in rows], marker="o", linewidth=2)
    ax.set_xlabel("m-bit LSB")
    ax.set_ylabel("PSNR (dB)")
    ax.set_title("PSNR terhadap m pada payload 100% kapasitas")
    ax.grid(True, alpha=.35)
    fig.tight_layout()
    fig.savefig(p / "grafik_psnr.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), dpi=150)
    for ax, image, row in zip(axes.flat, previews, rows):
        ax.imshow(image[::8, ::8])
        ax.set_title(f"m={row['m']}; PSNR={row['psnr_db']:.2f} dB")
        ax.axis("off")
    fig.suptitle("Stego-image payload acak 100% kapasitas", fontsize=14)
    fig.tight_layout()
    fig.savefig(p / "perbandingan_stego_m1_m4.png")
    plt.close(fig)
    lines = ["P3 — m-bit LSB, payload acak 100% kapasitas"]
    lines += [f"m={x['m']} | {x['capacity_kb']:.2f} KB | MSE={x['mse']:.6f} | PSNR={x['psnr_db']:.4f} dB" for x in rows]
    lines += [
        "Catatan: header=False disengaja agar payload mengisi 100% kapasitas.",
        "Tujuannya mengukur MSE/PSNR pada beban maksimum, bukan untuk round-trip.",
        "Karena itu stego P3 tidak memuat header 32-bit dan bukan artefak payload round-trip.",
    ]
    console_image(lines, SCREENSHOTS / "p3_console.png", "Output P3")
    results["p3"] = rows


def run_p4(cover: np.ndarray, payload: bytes, results: dict) -> None:
    p = OUT / "p4"
    encrypted = xor_keystream(payload, ENCRYPTION_SEED)
    stego = embed_random(cover, encrypted, NIM)
    save_rgb(stego, p / "stego_encrypted_random.png")
    retrieved, position_status = extract_random(stego, NIM)
    correct = xor_keystream(retrieved, ENCRYPTION_SEED) if retrieved else None
    wrong_encryption = xor_keystream(retrieved, ENCRYPTION_SEED + 1) if retrieved else None
    wrong_position, wrong_position_status = extract_random(stego, WRONG_SEED)
    lines = [
        "P4 — Kombinasi kriptografi dan steganografi",
        f"Key posisi benar ({NIM}) + key enkripsi benar ({ENCRYPTION_SEED}): {correct.decode('utf-8') if correct else None}",
        f"Key posisi benar + key enkripsi salah ({ENCRYPTION_SEED + 1}): {wrong_encryption.hex()[:128] if wrong_encryption else None}",
        f"Key posisi salah ({WRONG_SEED}): {wrong_position.decode('utf-8', errors='replace') if wrong_position else None}",
        f"Status posisi benar: {position_status}",
        f"Status posisi salah: {wrong_position_status}",
    ]
    console_image(lines, SCREENSHOTS / "p4_console.png", "Output P4")
    results["p4"] = {
        "correct_keys": correct.decode("utf-8") if correct else None,
        "wrong_encryption_key_hex": wrong_encryption.hex() if wrong_encryption else None,
        "wrong_position_status": wrong_position_status,
    }


def run_p5(cover: np.ndarray, payload: bytes, results: dict) -> None:
    p = OUT / "p5"
    stego = embed_sequential(cover, payload)
    png_path = p / "stego.png"
    bmp_path = p / "stego.bmp"
    jpeg_path = p / "stego_q95.jpg"
    save_rgb(stego, png_path)
    save_rgb(stego, bmp_path)
    save_rgb(stego, jpeg_path, quality=95, subsampling=0)
    expected = bits_from_bytes(payload)
    rows = []
    for name, path in (("PNG", png_path), ("BMP", bmp_path), ("JPEG quality=95", jpeg_path)):
        image = load_rgb(path)
        actual = extract_sequential_bits(image, len(expected), 1, 32)
        raw, status = extract_sequential(image)
        rows.append({
            "format": name,
            "ber_percent": bit_error_rate(expected, actual),
            "header_status": status,
            "decoded": raw.decode("utf-8", errors="replace") if raw else None,
        })
    lines = ["P5 — Pengaruh format file"]
    lines += [f"{x['format']}: BER={x['ber_percent']:.6f}% | {x['header_status']} | ekstraksi={x['decoded']}" for x in rows]
    console_image(lines, SCREENSHOTS / "p5_console.png", "Output P5")
    results["p5"] = rows


def run_bonus(cover: np.ndarray, results: dict) -> None:
    p = OUT / "bonus"
    # 50% capacity after header; deterministic data produces a meaningful LSB-plane comparison.
    bits = (cover.size // 2) - 32
    payload = np.random.default_rng(NIM).integers(0, 256, bits // 8, dtype=np.uint8).tobytes()
    stego = embed_sequential(cover, payload)
    save_rgb(stego, p / "stego_sequential_50_percent.png")
    cover_plane = (cover & 1) * 255
    stego_plane = (stego & 1) * 255
    save_rgb(cover_plane, p / "lsb_plane_cover.png")
    save_rgb(stego_plane, p / "lsb_plane_stego_50_percent.png")
    results["bonus"] = {"payload_bits": len(payload) * 8}


def main() -> None:
    for directory in [OUT / f"p{i}" for i in range(1, 6)] + [OUT / "bonus", SCREENSHOTS]:
        directory.mkdir(parents=True, exist_ok=True)
    cover = load_rgb(COVER)
    payload = MESSAGE.encode("utf-8")
    results: dict = {"message": MESSAGE, "cover": {"shape": list(cover.shape), "capacity_bits_1_lsb": int(cover.size)}}
    run_p1(cover, payload, results)
    run_p2(cover, payload, results)
    run_p3(cover, results)
    run_p4(cover, payload, results)
    run_p5(cover, payload, results)
    run_bonus(cover, results)
    (OUT / "hasil_eksperimen.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
