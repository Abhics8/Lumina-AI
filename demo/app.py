"""
Lumina AI - Visual Commerce Demo
Deploy to Hugging Face Spaces (FREE CPU tier)
"""

import gradio as gr
import torch
import numpy as np
from PIL import Image, ImageDraw

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ===== LAZY MODEL LOADING =====
_models = {}

def get_clip():
    if "clip" not in _models:
        from transformers import CLIPProcessor, CLIPModel
        print("Loading CLIP...")
        _models["clip_proc"] = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _models["clip"] = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE).eval()
        print("CLIP loaded!")
    return _models["clip_proc"], _models["clip"]

def get_owlv2():
    if "owl" not in _models:
        from transformers import Owlv2Processor, Owlv2ForObjectDetection
        print("Loading OWLv2...")
        _models["owl_proc"] = Owlv2Processor.from_pretrained("google/owlv2-base-patch16-ensemble")
        _models["owl"] = Owlv2ForObjectDetection.from_pretrained("google/owlv2-base-patch16-ensemble").to(DEVICE).eval()
        print("OWLv2 loaded!")
    return _models["owl_proc"], _models["owl"]

def encode_text(texts):
    """Encode text using CLIP text encoder - works on ALL transformers versions"""
    proc, model = get_clip()
    inputs = proc(text=texts, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
    with torch.no_grad():
        # Use text_model + text_projection directly (avoids API version issues)
        text_out = model.text_model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
        )
        embeds = model.text_projection(text_out.pooler_output)
        embeds = embeds / embeds.norm(dim=-1, keepdim=True)
    return embeds

def encode_image(image):
    """Encode image using CLIP vision encoder"""
    proc, model = get_clip()
    inputs = proc(images=image, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        vis_out = model.vision_model(pixel_values=inputs["pixel_values"])
        embeds = model.visual_projection(vis_out.pooler_output)
        embeds = embeds / embeds.norm(dim=-1, keepdim=True)
    return embeds


# ===== TAB 1: OBJECT DETECTION =====
FASHION_ITEMS = ["dress", "shirt", "pants", "shoes", "bag", "jacket", "hat", "sunglasses", "skirt", "coat", "watch", "belt"]
COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9", "#F1948A", "#82E0AA"]

def detect_fashion(image):
    if image is None:
        return None, "Please upload an image first"
    try:
        proc, model = get_owlv2()
        image = image.convert("RGB")
        inputs = proc(text=[FASHION_ITEMS], images=image, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            outputs = model(**inputs)
        target_sizes = torch.tensor([image.size[::-1]]).to(DEVICE)
        results = proc.image_processor.post_process_object_detection(outputs=outputs, target_sizes=target_sizes, threshold=0.1)[0]

        draw = ImageDraw.Draw(image)
        lines = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            coords = [round(i, 1) for i in box.cpu().tolist()]
            name = FASHION_ITEMS[label]
            conf = round(score.item() * 100, 1)
            color = COLORS[label % len(COLORS)]
            draw.rectangle(coords, outline=color, width=3)
            draw.text((coords[0] + 4, coords[1] + 4), f"{name} {conf}%", fill=color)
            lines.append(f"**{name.title()}** — {conf}%")

        text = f"### Detected {len(lines)} item(s)\n\n" + "\n\n".join(lines) if lines else "No fashion items found. Try a clearer photo!"
        return image, text
    except Exception as e:
        return image, f"Error: {e}"


# ===== TAB 2: VIBE CHECK =====
def vibe_check(image):
    if image is None:
        return "Please upload an image first"
    try:
        image = image.convert("RGB")

        occasions = ["casual everyday", "formal business", "party night out",
                      "beach vacation", "wedding guest", "gym workout",
                      "date night", "office professional"]
        vibes = ["bohemian", "minimalist", "vintage retro", "streetwear",
                 "elegant luxury", "sporty athletic", "edgy punk", "preppy classic"]

        all_labels = occasions + vibes
        text_emb = encode_text(all_labels)
        img_emb = encode_image(image)

        sims = (img_emb @ text_emb.T).squeeze(0).cpu().numpy()

        occ_scores = list(zip(occasions, sims[:len(occasions)]))
        vib_scores = list(zip(vibes, sims[len(occasions):]))
        occ_scores.sort(key=lambda x: -x[1])
        vib_scores.sort(key=lambda x: -x[1])

        r = f"## Style Analysis\n\n"
        r += f"### Occasion: **{occ_scores[0][0].title()}** ({occ_scores[0][1]*100:.0f}%)\n"
        r += f"### Vibe: **{vib_scores[0][0].title()}** ({vib_scores[0][1]*100:.0f}%)\n\n"
        r += "| Occasion | Score |\n|---|---|\n"
        for name, s in occ_scores[:5]:
            r += f"| {name.title()} | {s*100:.1f}% |\n"
        r += "\n| Vibe | Score |\n|---|---|\n"
        for name, s in vib_scores[:5]:
            r += f"| {name.title()} | {s*100:.1f}% |\n"
        return r
    except Exception as e:
        return f"Error: {e}"


# ===== TAB 3: SEMANTIC SEARCH =====
PRODUCTS = [
    {"name": "Red Floral Maxi Dress", "cat": "Dresses", "price": 49.99, "desc": "bohemian red summer dress with floral print"},
    {"name": "Classic Blue Denim Jacket", "cat": "Outerwear", "price": 79.99, "desc": "casual blue denim trucker jacket"},
    {"name": "White Canvas Sneakers", "cat": "Shoes", "price": 59.99, "desc": "minimalist white low top canvas sneakers"},
    {"name": "Black Leather Crossbody Bag", "cat": "Bags", "price": 129.99, "desc": "elegant black leather crossbody handbag"},
    {"name": "Gold Aviator Sunglasses", "cat": "Accessories", "price": 89.99, "desc": "vintage gold frame aviator sunglasses"},
    {"name": "Navy Slim Fit Chinos", "cat": "Pants", "price": 44.99, "desc": "smart casual navy blue slim fit chino pants"},
    {"name": "Cream Silk Blouse", "cat": "Tops", "price": 69.99, "desc": "elegant cream silk button up blouse formal"},
    {"name": "Black Running Shoes", "cat": "Shoes", "price": 99.99, "desc": "sporty black athletic running shoes"},
    {"name": "Grey Wool Overcoat", "cat": "Outerwear", "price": 199.99, "desc": "formal grey wool long overcoat for winter"},
    {"name": "Striped Cotton T-Shirt", "cat": "Tops", "price": 24.99, "desc": "casual blue white striped cotton t-shirt"},
    {"name": "Pleated Satin Midi Skirt", "cat": "Skirts", "price": 54.99, "desc": "elegant pleated satin midi skirt formal"},
    {"name": "Canvas Messenger Bag", "cat": "Bags", "price": 39.99, "desc": "casual canvas crossbody messenger bag"},
]

_prod_emb = None

def get_product_embeddings():
    global _prod_emb
    if _prod_emb is None:
        _prod_emb = encode_text([p["desc"] for p in PRODUCTS])
    return _prod_emb

def search(query):
    if not query or not query.strip():
        return "Please enter a search query"
    try:
        query_emb = encode_text([query])
        prod_emb = get_product_embeddings()
        sims = (query_emb @ prod_emb.T).squeeze(0).cpu().numpy()
        top = sims.argsort()[::-1][:5]

        r = f"## Results for \"{query}\"\n\n"
        for rank, i in enumerate(top, 1):
            p = PRODUCTS[i]
            r += f"**{rank}. {p['name']}** — ${p['price']}\n- Category: {p['cat']} | Match: {sims[i]*100:.1f}%\n\n"
        return r
    except Exception as e:
        return f"Error: {e}"


# ===== UI =====
with gr.Blocks(title="Lumina AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Lumina AI — Visual Commerce Engine\n*AI-powered fashion search using OWLv2 + CLIP*")
    with gr.Tabs():
        with gr.Tab("Detect Items"):
            with gr.Row():
                with gr.Column():
                    d_in = gr.Image(type="pil", label="Upload Fashion Photo")
                    d_btn = gr.Button("Detect", variant="primary", size="lg")
                with gr.Column():
                    d_img = gr.Image(label="Results")
                    d_txt = gr.Markdown()
            d_btn.click(detect_fashion, d_in, [d_img, d_txt])

        with gr.Tab("Vibe Check"):
            with gr.Row():
                with gr.Column():
                    v_in = gr.Image(type="pil", label="Upload Outfit")
                    v_btn = gr.Button("Analyze", variant="primary", size="lg")
                with gr.Column():
                    v_out = gr.Markdown()
            v_btn.click(vibe_check, v_in, v_out)

        with gr.Tab("Search"):
            with gr.Row():
                with gr.Column():
                    s_in = gr.Textbox(label="Search", placeholder="e.g. red dress for summer party")
                    gr.Examples(["elegant black evening dress", "casual weekend jacket", "vintage sunglasses", "sporty running shoes"], s_in)
                    s_btn = gr.Button("Search", variant="primary", size="lg")
                with gr.Column():
                    s_out = gr.Markdown()
            s_btn.click(search, s_in, s_out)

    gr.Markdown("---\nBuilt by [Abhi Bhardwaj](https://github.com/Abhics8) | [GitHub](https://github.com/Abhics8/Lumina-AI)")

if __name__ == "__main__":
    demo.launch()
