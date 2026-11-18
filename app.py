"""
UI Streamlit -- file ini HANYA mengurus tampilan, upload, dan download.
Semua logic kompresi ada di folder backend/, dipanggil sebagai fungsi.
"""

import os
import tempfile
import uuid
import io
from typing import List, Dict, Any

import streamlit as st
from PIL import Image

from backend.pdf_compressor import compress_pdf
from backend.image_compressor import compress_image
from backend.ppt_compressor import compress_pptx
from backend.video_compressor import compress_video
from backend.audio_compressor import compress_audio
from backend.image_to_pdf import generate_pdf
from backend.pdf_cropper import crop_pdf, render_page_preview, get_pdf_info
from backend.qr_generator import generate_qr


st.set_page_config(page_title="File Compressor", page_icon="🗜️", layout="centered")
st.title("🗜️ File Compressor")
st.caption("Kompresi PDF, gambar, PPTX, video, dan audio — UI dan backend terpisah")

# Session state initialization
if "images_to_pdf" not in st.session_state:
    st.session_state.images_to_pdf = []
if "pdf_settings" not in st.session_state:
    st.session_state.pdf_settings = {
        "layout": "1_per_page",
        "orientation": "portrait",
        "margin_mm": 10,
        "quality": 90,
    }
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "compressed_file" not in st.session_state:
    st.session_state.compressed_file = None  # {"bytes": ..., "ext": ..., "default_name": ...}


FILE_TYPES = {
    "PDF": ["pdf"],
    "Gambar (JPG/PNG)": ["jpg", "jpeg", "png"],
    "PowerPoint (PPTX)": ["pptx"],
    "Video": ["mp4", "mov", "avi", "mkv"],
    "Audio": ["mp3", "wav", "m4a", "aac", "ogg", "flac", "wma"],
}

# Main tabs
tab_compress, tab_images_pdf, tab_pdf_crop, tab_qr = st.tabs([
    "🗜️ Kompres File",
    "📄 Images → PDF",
    "✂️ Potong PDF",
    "📱 QR Generator",
])

# ==================== TAB 1: KOMPRES FILE (EXISTING) ====================
with tab_compress:
    file_type = st.selectbox("Pilih jenis file", list(FILE_TYPES.keys()))
    uploaded_file = st.file_uploader("Upload file", type=FILE_TYPES[file_type])

    # opsi kompresi disesuaikan per jenis file
    if file_type == "PDF":
        quality = st.slider("Kualitas gambar dalam PDF", 10, 100, 50)
    elif file_type == "Gambar (JPG/PNG)":
        quality = st.slider("Kualitas JPEG", 10, 100, 70)
    elif file_type == "PowerPoint (PPTX)":
        quality = st.slider("Kualitas gambar dalam slide", 10, 100, 60)
    elif file_type == "Audio":
        bitrate_presets = ["64k", "96k", "128k", "192k", "256k", "320k"]
        bitrate_idx = st.selectbox(
            "Bitrate",
            options=range(len(bitrate_presets)),
            format_func=lambda i: bitrate_presets[i],
            index=2,  # default 128k
            key="audio_bitrate_idx",
        )
        selected_bitrate = bitrate_presets[bitrate_idx]
        convert_to_mp3 = st.checkbox(
            "Konversi ke MP3 (bitrate tetap)",
            value=False,
            key="audio_convert_mp3",
        )
    else:
        crf = st.slider("CRF video (makin besar = makin kecil, kualitas turun)", 18, 35, 28)

    if uploaded_file and st.button("Kompres sekarang", type="primary"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            output_path = os.path.join(tmp_dir, "compressed_" + uploaded_file.name)

            with st.spinner("Sedang mengompres, mohon tunggu..."):
                try:
                    if file_type == "PDF":
                        compress_pdf(input_path, output_path, image_quality=quality)
                    elif file_type == "Gambar (JPG/PNG)":
                        compress_image(input_path, output_path, quality=quality)
                    elif file_type == "PowerPoint (PPTX)":
                        compress_pptx(input_path, output_path, quality=quality)
                    elif file_type == "Audio":
                        output_path = compress_audio(
                            input_path,
                            output_path,
                            bitrate=selected_bitrate,
                            convert_to_mp3=convert_to_mp3,
                        )
                    else:
                        compress_video(input_path, output_path, crf=crf)
                except Exception as e:
                    st.error(f"Terjadi error saat kompresi: {e}")
                    st.stop()

            original_mb = os.path.getsize(input_path) / (1024 * 1024)
            compressed_mb = os.path.getsize(output_path) / (1024 * 1024)
            saved_pct = (1 - compressed_mb / original_mb) * 100 if original_mb > 0 else 0

            st.success(
                f"Selesai! {original_mb:.2f} MB → {compressed_mb:.2f} MB "
                f"(hemat {saved_pct:.1f}%)"
            )

            # Store compressed file in session state for persistent download UI
            _, ext = os.path.splitext(output_path)
            default_name = os.path.splitext(os.path.basename(output_path))[0]
            with open(output_path, "rb") as f:
                file_bytes = f.read()
            st.session_state.compressed_file = {
                "bytes": file_bytes,
                "ext": ext,
                "default_name": default_name,
            }

    # Show download section if file was compressed (outside button block)
    if st.session_state.compressed_file is not None:
        cf = st.session_state.compressed_file
        custom_name = st.text_input(
            "Nama file (tanpa ekstensi)",
            value=cf["default_name"],
            key="download_name_compressed",
        )
        if not custom_name.strip():
            custom_name = cf["default_name"]

        final_name = custom_name.strip() + cf["ext"]

        st.download_button(
            "⬇️ Download hasil kompresi",
            data=cf["bytes"],
            file_name=final_name,
        )

# ==================== TAB 2: IMAGES → PDF (NEW) ====================
with tab_images_pdf:
    st.header("📄 Images → PDF")
    st.caption("Gabungkan beberapa gambar menjadi satu PDF dengan edit foto")

    # Upload section
    uploaded_files = st.file_uploader(
        "Upload gambar (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="images_pdf_uploader",
    )

    # Process uploads
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Check if already added (by name + size)
            exists = any(
                img["name"] == uploaded_file.name and img.get("size") == uploaded_file.size
                for img in st.session_state.images_to_pdf
            )
            if not exists:
                try:
                    img_bytes = uploaded_file.read()
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    if pil_img.mode in ("RGBA", "P", "LA"):
                        pil_img = pil_img.convert("RGB")
                    st.session_state.images_to_pdf.append({
                        "id": str(uuid.uuid4()),
                        "name": uploaded_file.name,
                        "size": uploaded_file.size,
                        "original": pil_img,
                        "edited": pil_img.copy(),
                        "edit": {"rotation": 0, "crop": {"x": 0, "y": 0, "w": 0, "h": 0}},
                    })
                except Exception as e:
                    st.error(f"Gagal membaca {uploaded_file.name}: {e}")

    # Show grid preview
    images = st.session_state.images_to_pdf
    if images:
        st.subheader("Pratinjau Gambar")

        # Grid layout - 3 columns
        cols_per_row = 3
        for i in range(0, len(images), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(images):
                    break

                img_data = images[idx]
                with col:
                    # Thumbnail
                    thumb = img_data["edited"].copy()
                    thumb.thumbnail((200, 200))
                    st.image(thumb, use_container_width=True)

                    # Buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✏️ Edit", key=f"edit_{img_data['id']}", use_container_width=True):
                            st.session_state.edit_idx = idx
                            st.rerun()
                    with btn_col2:
                        if st.button("🗑️ Hapus", key=f"delete_{img_data['id']}", use_container_width=True):
                            st.session_state.images_to_pdf.pop(idx)
                            if st.session_state.edit_idx == idx:
                                st.session_state.edit_idx = None
                            elif st.session_state.edit_idx is not None and st.session_state.edit_idx > idx:
                                st.session_state.edit_idx -= 1
                            st.rerun()

                    st.caption(img_data["name"])

    # Edit modal
    if st.session_state.edit_idx is not None and st.session_state.edit_idx < len(images):
        idx = st.session_state.edit_idx
        img_data = images[idx]

        with st.expander("✏️ Editor Gambar", expanded=True):
            st.markdown(f"**Mengedit: {img_data['name']}**")

            # Show current edited image
            from backend.image_to_pdf import apply_edits as _apply_edits
            preview_img = _apply_edits(img_data["original"], img_data["edit"]).copy()
            preview_img.thumbnail((500, 500))
            st.image(preview_img, caption="Pratinjau hasil edit", use_container_width=True)

            # Rotation controls
            st.markdown("**Rotasi**")
            rot_col1, rot_col2, rot_col3, rot_col4 = st.columns(4)
            with rot_col1:
                if st.button("↻ 90°", key=f"rot90_{img_data['id']}", use_container_width=True):
                    img_data["edit"]["rotation"] = (img_data["edit"]["rotation"] + 90) % 360
                    st.session_state[f"rot_select_{img_data['id']}"] = img_data["edit"]["rotation"]
                    st.rerun()
            with rot_col2:
                if st.button("↺ -90°", key=f"rot-90_{img_data['id']}", use_container_width=True):
                    img_data["edit"]["rotation"] = (img_data["edit"]["rotation"] - 90) % 360
                    st.session_state[f"rot_select_{img_data['id']}"] = img_data["edit"]["rotation"]
                    st.rerun()
            with rot_col3:
                if st.button("↻ 180°", key=f"rot180_{img_data['id']}", use_container_width=True):
                    img_data["edit"]["rotation"] = (img_data["edit"]["rotation"] + 180) % 360
                    st.session_state[f"rot_select_{img_data['id']}"] = img_data["edit"]["rotation"]
                    st.rerun()
            with rot_col4:
                rotation = st.selectbox(
                    "Sudut",
                    [0, 90, 180, 270],
                    index=[0, 90, 180, 270].index(img_data["edit"]["rotation"] % 360),
                    key=f"rot_select_{img_data['id']}",
                )
                if rotation != img_data["edit"]["rotation"]:
                    img_data["edit"]["rotation"] = rotation
                    st.rerun()

            # Crop controls
            st.markdown("**Crop (koordinat piksel)**")
            crop = img_data["edit"]["crop"]
            orig_w, orig_h = img_data["original"].size

            crop_col1, crop_col2, crop_col3, crop_col4 = st.columns(4)
            with crop_col1:
                crop["x"] = st.number_input("X", min_value=0, max_value=max(0, orig_w - 1), value=crop["x"], step=1, key=f"crop_x_{img_data['id']}")
            with crop_col2:
                crop["y"] = st.number_input("Y", min_value=0, max_value=max(0, orig_h - 1), value=crop["y"], step=1, key=f"crop_y_{img_data['id']}")
            with crop_col3:
                crop["w"] = st.number_input("W", min_value=0, max_value=orig_w, value=crop["w"], step=1, key=f"crop_w_{img_data['id']}")
            with crop_col4:
                crop["h"] = st.number_input("H", min_value=0, max_value=orig_h, value=crop["h"], step=1, key=f"crop_h_{img_data['id']}")

            crop_btn_col1, crop_btn2 = st.columns(2)
            with crop_btn_col1:
                if st.button("🎯 Auto-fit", key=f"autofit_{img_data['id']}", use_container_width=True):
                    crop["x"] = 0
                    crop["y"] = 0
                    crop["w"] = 0
                    crop["h"] = 0
                    st.rerun()
            with crop_btn2:
                if st.button("🔄 Reset Crop", key=f"resetcrop_{img_data['id']}", use_container_width=True):
                    crop["x"] = 0
                    crop["y"] = 0
                    crop["w"] = 0
                    crop["h"] = 0
                    st.rerun()

            # Save / Cancel
            save_col1, save_col2 = st.columns(2)
            with save_col1:
                if st.button("✅ Simpan Edit", key=f"save_{img_data['id']}", type="primary", use_container_width=True):
                    # Apply edits to edited image for preview
                    from backend.image_to_pdf import apply_edits
                    try:
                        img_data["edited"] = apply_edits(img_data["original"], img_data["edit"])
                    except Exception as e:
                        st.error(f"Gagal menerapkan edit: {e}")
                    st.session_state.edit_idx = None
                    st.rerun()
            with save_col2:
                if st.button("❌ Batal", key=f"cancel_{img_data['id']}", use_container_width=True):
                    st.session_state.edit_idx = None
                    st.rerun()

    # PDF Settings
    if images:
        st.divider()
        st.subheader("⚙️ Pengaturan Output PDF")

        set_col1, set_col2 = st.columns(2)
        with set_col1:
            layout_label = st.selectbox(
                "Layout",
                ["1 gambar per halaman", "2 gambar per halaman (grid)"],
                index=0 if st.session_state.pdf_settings["layout"] == "1_per_page" else 1,
                key="pdf_layout",
            )
            st.session_state.pdf_settings["layout"] = "1_per_page" if layout_label == "1 gambar per halaman" else "2_per_page_grid"

            orientation_label = st.selectbox(
                "Orientasi",
                ["Portrait", "Landscape"],
                index=0 if st.session_state.pdf_settings["orientation"] == "portrait" else 1,
                key="pdf_orientation",
            )
            st.session_state.pdf_settings["orientation"] = "portrait" if orientation_label == "Portrait" else "landscape"

        with set_col2:
            st.session_state.pdf_settings["margin_mm"] = st.number_input(
                "Margin (mm)",
                min_value=0,
                max_value=50,
                value=st.session_state.pdf_settings["margin_mm"],
                step=1,
                key="pdf_margin",
            )
            st.session_state.pdf_settings["quality"] = st.slider(
                "Kualitas gambar (0-100)",
                min_value=10,
                max_value=100,
                value=st.session_state.pdf_settings["quality"],
                key="pdf_quality",
            )

        # Generate button
        if st.button("🔄 Generate PDF", type="primary", use_container_width=True):
            with st.spinner("Membuat PDF..."):
                try:
                    # Prepare image dicts for backend
                    image_dicts = [
                        {"original": img["original"], "edit": img["edit"]}
                        for img in images
                    ]

                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        output_path = tmp.name

                    st.session_state.pdf_bytes = generate_pdf(image_dicts, st.session_state.pdf_settings, output_path)

                    st.success(f"PDF berhasil dibuat! ({len(images)} gambar, {len(st.session_state.pdf_bytes) / 1024:.1f} KB)")

                    # Cleanup temp file
                    try:
                        os.unlink(output_path)
                    except:
                        pass

                except Exception as e:
                    st.error(f"Gagal membuat PDF: {e}")

        # Show download section if PDF was generated (outside button block)
        if st.session_state.pdf_bytes is not None:
            pdf_name = st.text_input(
                "Nama file PDF (tanpa ekstensi)",
                value="images_merged",
                key="pdf_download_name",
            )
            if not pdf_name.strip():
                pdf_name = "images_merged"

            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state.pdf_bytes,
                file_name=pdf_name.strip() + ".pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    else:
        st.info("Upload minimal satu gambar untuk memulai.")

# ==================== TAB 3: POTONG PDF (CROP) ====================
with tab_pdf_crop:
    st.header("✂️ Potong PDF")
    st.caption("Potong tepi halaman PDF — cocok untuk hapus watermark CamScanner di bagian bawah")

    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_crop_uploader")

    if uploaded_pdf:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = os.path.join(tmp_dir, uploaded_pdf.name)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer() if False else uploaded_pdf.getbuffer())

            info = get_pdf_info(input_path)
            st.info(f"{info['page_count']} halaman • Ukuran halaman: {info['first_page_size'][0]:.0f} × {info['first_page_size'][1]:.0f} pt")

            # Crop controls
            st.markdown("**Persentase crop dari setiap tepi**")
            col1, col2 = st.columns(2)
            with col1:
                top_pct = st.slider("Atas (%)", 0, 50, 0, 1)
                bottom_pct = st.slider("Bawah (%)", 0, 50, 8, 1)
            with col2:
                left_pct = st.slider("Kiri (%)", 0, 50, 0, 1)
                right_pct = st.slider("Kanan (%)", 0, 50, 0, 1)

            # Preview before/after
            st.markdown("**Pratinjau halaman 1**")
            prev_col1, prev_col2 = st.columns(2)
            with prev_col1:
                st.markdown("*Sebelum*")
                img_before = render_page_preview(input_path, 0, dpi=100)
                st.image(img_before, use_container_width=True)
            with prev_col2:
                st.markdown("*Sesudah*")
                img_after = render_page_preview(input_path, 0, dpi=100,
                                                crop_pcts=(top_pct, bottom_pct, left_pct, right_pct))
                st.image(img_after, use_container_width=True)

            # Generate button
            if st.button("✂️ Potong PDF", type="primary", use_container_width=True):
                with st.spinner("Memotong PDF..."):
                    try:
                        output_path = os.path.join(tmp_dir, "cropped_" + uploaded_pdf.name)
                        crop_pdf(input_path, output_path,
                                 top_pct=top_pct, bottom_pct=bottom_pct,
                                 left_pct=left_pct, right_pct=right_pct)

                        with open(output_path, "rb") as f:
                            cropped_bytes = f.read()

                        st.session_state.cropped_pdf = {
                            "bytes": cropped_bytes,
                            "ext": ".pdf",
                            "default_name": "cropped_" + os.path.splitext(uploaded_pdf.name)[0],
                        }
                        st.success(f"PDF berhasil dipotong! ({len(cropped_bytes) / 1024:.1f} KB)")
                    except Exception as e:
                        st.error(f"Gagal memotong PDF: {e}")

    # Show download section if PDF was cropped (outside button block)
    if st.session_state.get("cropped_pdf") is not None:
        cp = st.session_state.cropped_pdf
        crop_name = st.text_input(
            "Nama file PDF (tanpa ekstensi)",
            value=cp["default_name"],
            key="cropped_pdf_name",
        )
        if not crop_name.strip():
            crop_name = cp["default_name"]

        st.download_button(
            "⬇️ Download PDF hasil crop",
            data=cp["bytes"],
            file_name=crop_name.strip() + cp["ext"],
            mime="application/pdf",
            use_container_width=True,
        )

# ==================== TAB 4: QR GENERATOR ====================
with tab_qr:
    st.header("📱 QR Generator")
    st.caption("Generate QR code statis dari teks/URL apa pun")

    # Input data
    qr_data = st.text_area(
        "Teks atau URL yang ingin Anda encode",
        height=100,
        placeholder="https://example.com atau teks biasa...",
    )

    # Options in columns
    opt_col1, opt_col2 = st.columns(2)
    with opt_col1:
        box_size = st.slider("Ukuran kotak (module)", 5, 20, 10, 1)
        border = st.slider("Border (quiet zone)", 1, 10, 4, 1)
        fill_color = st.color_picker("Warna QR", "#000000")
    with opt_col2:
        back_color = st.color_picker("Warna background", "#FFFFFF")
        # Preset colors
        preset_colors = st.selectbox(
            "Preset warna (opsional)",
            ["Custom"] + ["Black on White", "White on Black", "Blue on Yellow", "Green on White"],
        )
        if preset_colors != "Custom":
            if preset_colors == "Black on White":
                fill_color, back_color = "black", "white"
            elif preset_colors == "White on Black":
                fill_color, back_color = "white", "black"
            elif preset_colors == "Blue on Yellow":
                fill_color, back_color = "blue", "yellow"
            elif preset_colors == "Green on White":
                fill_color, back_color = "green", "white"

    # Generate button
    if st.button("🔄 Generate QR Code", type="primary", use_container_width=True):
        if not qr_data.strip():
            st.warning("Masukkan teks atau URL terlebih dahulu")
        else:
            with st.spinner("Membuat QR code..."):
                try:
                    qr_img = generate_qr(
                        qr_data,
                        box_size=box_size,
                        border=border,
                        fill_color=fill_color,
                        back_color=back_color,
                    )

                    # Store in session state for download
                    import io
                    img_bytes = io.BytesIO()
                    qr_img.save(img_bytes, format="PNG")
                    st.session_state.qr_bytes = img_bytes.getvalue()

                    st.success("QR code berhasil dibuat!")
                except Exception as e:
                    st.error(f"Gagal membuat QR code: {e}")

    # Download section
    if "qr_bytes" in st.session_state and st.session_state.qr_bytes:
        st.divider()
        qr_name = st.text_input(
            "Nama file QR (tanpa ekstensi)",
            value="qr_code",
            key="qr_download_name",
        )
        if not qr_name.strip():
            qr_name = "qr_code"

        st.download_button(
            "⬇️ Download QR Code",
            data=st.session_state.qr_bytes,
            file_name=qr_name.strip() + ".png",
            mime="image/png",
            use_container_width=True,
        )

    # Preview (if QR generated)
    if "qr_bytes" in st.session_state and st.session_state.qr_bytes:
        st.divider()
        st.subheader("Pratinjau QR Code")
        st.image(st.session_state.qr_bytes, use_container_width=True)