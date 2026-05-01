import re

from django.conf import settings

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - handled via fallback
    genai = None


def get_gemini_model():
    if not getattr(settings, 'GEMINI_CHAT_ENABLED', False):
        return None

    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    model_name = getattr(settings, 'GEMINI_CHAT_MODEL', None)
    if not api_key or not model_name or genai is None:
        return None

    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name=model_name)
    except Exception as exc:  # pragma: no cover - SDK setup behavior
        print("Gemini Client Error:", exc)
        return None


def fallback_product_reply(user_message, product_context, assistant_context=''):
    msg = (user_message or '').lower().strip()
    cleaned_msg = re.sub(r'[^a-z0-9\s-]', ' ', msg)
    keywords = [word for word in cleaned_msg.split() if len(word) > 2]
    query_hint = ' '.join(keywords[:3]) if keywords else (msg or 'your query')

    parts = []
    support_context = (assistant_context or '').lower()
    support_path = '/need-help/' if 'support_path=/need-help/' in support_context else ''

    support_line = ''
    if 'support_intent=greeting' in support_context:
        support_line = "Good to see you! Welcome to VASU. Tell me what you are looking for and I will help you quickly."
    if 'support_intent=order_help' in support_context:
        support_line = (
            "To place an order: open a product, add it to cart, go to My Bag, "
            "then checkout with address and payment details."
        )
    elif 'support_intent=shipping' in support_context:
        support_line = "Shipping usually takes around 3 to 5 business days across India."
    elif 'support_intent=payment' in support_context:
        support_line = "You can pay using card, UPI, QR code, or cash on delivery."
    elif 'support_intent=return' in support_context:
        support_line = "Eligible unused items can be returned or exchanged within 7 days."
    elif 'support_intent=track' in support_context:
        support_line = "You can track your order from My Account in the Order History section."
    elif 'support_intent=vendor_account' in support_context:
        support_line = (
            "To request a vendor account, contact the VASU admin/support team from the Need Help page"
            + (f" ({support_path})" if support_path else "")
            + ". Choose Support Request and write 'Vendor Account Request' with your name, email, business details, and category."
        )

    if msg in {'hi', 'hello', 'hey'}:
        return "Hello! Welcome to Vasu Store. Tell me what you are looking for, and I will help you quickly."

    if support_line:
        parts.append(support_line)

    if "Database matches found" in product_context:
        parts.append("I found matching products for you. Please check the product cards shown below.")
        return ' '.join(parts)

    if support_line:
        return ' '.join(parts)

    parts.append(f"I could not find an exact product match for \"{query_hint}\" right now.")
    parts.append(
        "Try searching with product name, brand, color, or category "
        "(for example: black dress, white sneakers, tote bag)."
    )
    if not assistant_context:
        parts.append("I can also help with shipping, payment, returns, and order tracking.")
    return ' '.join(parts)


def safe_ai_reply(user_message, product_info, assistant_context=''):
    context_flags = (assistant_context or '').lower()
    is_smalltalk = 'smalltalk=true' in context_flags
    require_ai = 'require_ai=true' in context_flags

    if not product_info or "No products" in product_info:
        if is_smalltalk:
            product_context = "No product search is needed for this greeting query."
        else:
            product_context = "No products found in the database matching this query."
    else:
        product_context = f"Database matches found: {product_info}"

    model = get_gemini_model()
    if model is None:
        if require_ai:
            return "I am unable to reach the AI service right now. Please try again in a moment."
        return fallback_product_reply(user_message, product_context, assistant_context)

    prompt = f"""
    You are the Vasu Store customer assistant.
    Support Context: {assistant_context or 'No special support context'}
    Product Context: {product_context}
    Customer Query: {user_message}

    Rules:
    1. Always reply in English.
    2. Keep the response concise and friendly.
    3. Do not sound robotic or use fixed canned text.
    4. If matching products exist, mention that the user can review the product cards below.
    5. If this is a small-talk greeting (smalltalk=true), reply naturally and do not force product-search suggestions.
    6. If no products match in a shopping query, suggest searching by product name, category, color, or brand.
    6. If Support Context includes support_intent=..., answer that support intent clearly.
    7. If Support Context includes support_intent=vendor_account, guide the user to submit a vendor request via /need-help/.
    """

    timeout_seconds = getattr(settings, 'GEMINI_CHAT_TIMEOUT', 8.0)

    try:
        response = model.generate_content(
            prompt,
            request_options={'timeout': timeout_seconds},
        )
        output_text = getattr(response, 'text', '')
        if output_text and str(output_text).strip():
            return str(output_text).strip()

        for candidate in getattr(response, 'candidates', []) or []:
            content = getattr(candidate, 'content', None)
            parts = getattr(content, 'parts', []) if content else []
            text_chunks = [
                str(getattr(part, 'text', '')).strip()
                for part in parts
                if str(getattr(part, 'text', '')).strip()
            ]
            if text_chunks:
                return ' '.join(text_chunks)
    except Exception as exc:  # pragma: no cover - network/service behavior
        print("Gemini API Error:", exc)

    if require_ai:
        return "I am unable to reach the AI service right now. Please try again in a moment."

    return fallback_product_reply(user_message, product_context, assistant_context)


ai_reply = safe_ai_reply
