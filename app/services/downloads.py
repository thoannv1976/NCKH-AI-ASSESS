"""Đóng gói sản phẩm/minh chứng của giảng viên thành ZIP để Admin tải về.

ZIP được TẠO THEO LUỒNG (streaming): vừa đóng gói vừa gửi từng khối cho trình duyệt,
không dựng toàn bộ tệp tạm rồi mới gửi — nhờ vậy gói lớn (hàng trăm giảng viên) không
bị quá thời gian request của Cloud Run. Dùng ZIP_STORED (không nén) vì docx/pdf/pptx
đã nén sẵn → nhanh hơn nhiều và ít tốn CPU.

Cấu trúc: [<ĐơnVị>/]<MãGV_HọTên>/Phan<X>_SanPham|MinhChung/<tên tệp>, kèm
PhanA_ThongTin.txt, LIEN_KET.txt (các liên kết), và DANH_SACH.csv ở gốc (gói nhiều GV).
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterator

from app.config import get_settings, now_vn

_CHUNK = 1024 * 1024


def _safe(s: str | None) -> str:
    return re.sub(r"[^\w.\-]+", "_", (s or "").strip(), flags=re.UNICODE).strip("_") or "x"


def folder_name(user: dict) -> str:
    return f"{_safe(user.get('ma_gv') or 'SV')}_{_safe(user.get('ho_ten') or '')}"


def zip_filename(tag: str = "") -> str:
    return f"{get_settings().org_short}-SanPham{tag}-{now_vn():%Y%m%d-%H%M}.zip"


def _unique(seen: set[str], name: str) -> str:
    if name not in seen:
        seen.add(name)
        return name
    stem, dot, ext = name.rpartition(".")
    i = 2
    while True:
        cand = f"{stem}_{i}.{ext}" if dot else f"{name}_{i}"
        if cand not in seen:
            seen.add(cand)
            return cand
        i += 1


class _ChunkBuffer:
    """File-like để zipfile ghi vào; lấy dữ liệu ra theo khối qua take().

    Có tell() (zipfile cần vị trí để tính offset) nhưng KHÔNG có seek() → zipfile
    chuyển sang chế độ không seek (ghi data descriptor), phù hợp streaming.
    """

    def __init__(self) -> None:
        self._buf = bytearray()
        self._pos = 0

    def write(self, b: bytes) -> int:
        self._buf.extend(b)
        self._pos += len(b)
        return len(b)

    def tell(self) -> int:
        return self._pos

    def flush(self) -> None:
        pass

    def take(self) -> bytes:
        if not self._buf:
            return b""
        d = bytes(self._buf)
        self._buf.clear()
        return d


def _info_text(sub: dict, user: dict) -> str:
    pa = sub.get("part_a") or {}
    thanh_vien = pa.get("thanh_vien")
    if isinstance(thanh_vien, list):
        thanh_vien = ", ".join(thanh_vien)
    return (
        f"Tên công trình: {pa.get('ten_cong_trinh', '')}\n"
        f"Loại nghiên cứu: {pa.get('loai', '')}\n"
        f"Chủ nhiệm: {pa.get('ho_ten', '')}\n"
        f"MSSV chủ nhiệm: {pa.get('ma_gv', '')}\n"
        f"Đơn vị (Viện/Khoa/Cơ sở): {pa.get('khoa_bo_mon', '')}\n"
        f"Thành viên nhóm: {thanh_vien or ''}\n"
        f"Giảng viên hướng dẫn: {pa.get('gvhd', '')}\n"
        f"Trạng thái hồ sơ: {sub.get('status', '')}\n"
    )


def _add_submission_stream(zf, buf: _ChunkBuffer, store, storage, sub, user, base=""):
    """Ghi một hồ sơ vào zip, yield các khối dữ liệu. Trả về số tệp đã thêm."""
    items = store.find("submission_items", submission_id=sub["id"])
    folder = (base + "/" if base else "") + folder_name(user)
    zf.writestr(f"{folder}/PhanA_ThongTin.txt", _info_text(sub, user))
    if (out := buf.take()):
        yield out

    seen: set[str] = set()
    links: list[str] = []
    n_files = 0
    for it in items:
        part = it.get("part", "?")
        kind = "SanPham" if it.get("kind") == "product" else "MinhChung"
        if it.get("type") == "file":
            arc = _unique(seen, f"{folder}/Phan{part}_{kind}/{_safe(it.get('original_name'))}")
            try:
                with zf.open(arc, "w") as dest, storage.open(it["storage_path"]) as src:
                    while chunk := src.read(_CHUNK):
                        dest.write(chunk)
                        if (out := buf.take()):
                            yield out
                n_files += 1
            except Exception as exc:  # noqa: BLE001 — tệp lỗi ghi chú lại, không dừng cả gói
                zf.writestr(arc + ".LOI.txt", f"Không đọc được tệp: {exc}")
            if (out := buf.take()):
                yield out
        else:
            links.append(f"[Phần {part} · {kind}] {it.get('original_name') or ''}: {it.get('url')}")
    if links:
        zf.writestr(f"{folder}/LIEN_KET.txt", "\n".join(links))
        if (out := buf.take()):
            yield out
    return n_files


def stream_zip(store, storage, subs: list[dict], *, manifest: bool = False,
               base_by_khoa: bool = False) -> Iterator[bytes]:
    """Sinh luồng byte ZIP cho danh sách hồ sơ. manifest=True thêm DANH_SACH.csv ở gốc."""
    users = {u["id"]: u for u in store.all("users")}
    buf = _ChunkBuffer()
    rows = [["MSSV chủ nhiệm", "Chủ nhiệm", "Đơn vị", "Bộ môn/Ngành", "Vai trò", "Trạng thái", "Số tệp"]]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        for s in subs:
            u = users.get(s["user_id"]) or {}
            base = _safe(u.get("khoa") or "KhongRoDonVi") if base_by_khoa else ""
            n = yield from _add_submission_stream(zf, buf, store, storage, s, u, base=base)
            rows.append([u.get("ma_gv", ""), u.get("ho_ten", ""), u.get("khoa", ""),
                         u.get("bo_mon", ""), u.get("chuc_vu", ""), s.get("status", ""), n])
            if (out := buf.take()):
                yield out
        if manifest:
            sbuf = io.StringIO()
            csv.writer(sbuf).writerows(rows)
            zf.writestr("DANH_SACH.csv", "﻿" + sbuf.getvalue())  # BOM để Excel đọc tiếng Việt
            if (out := buf.take()):
                yield out
    if (out := buf.take()):
        yield out
