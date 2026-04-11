from django.conf import settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled via fallback
    OpenAI = None


def get_openai_client():
    if not getattr(settings, 'OPENAI_CHAT_ENABLED', False):
        return None

    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    model = getattr(settings, 'OPENAI_CHAT_MODEL', None)
    if not api_key or not model or OpenAI is None:
        return None

    return OpenAI(
        api_key=api_key,
        timeout=getattr(settings, 'OPENAI_CHAT_TIMEOUT', 6.0),
        max_retries=0,
    )


def fallback_product_reply(user_message, product_context):
    msg = (user_message or '').lower().strip()

    if msg in {'hi', 'hello', 'hey'}:
        return "Hello! Welcome to Vasu Store. How can I assist you today?"
    if 'return' in msg or 'exchange' in msg:
        return "Return Policy: You can return or exchange unused items within 7 days."
    if 'shipping' in msg or 'delivery' in msg:
        return "Shipping: We provide pan-India delivery within 3 to 5 business days."
    if 'payment' in msg or 'upi' in msg or 'card' in msg or 'cash' in msg:
        return "Payment options: card, UPI, QR code, and cash on delivery are available at checkout."

    if "Database matches found" in product_context:
        return "I found matching products for you. Please check the product cards shown below."
    return "I could not find an exact match. Try searching by product name, color, category, or brand."


def safe_ai_reply(user_message, product_info):
    if not product_info or "No products" in product_info:
        product_context = "No products found in the database matching this query."
    else:
        product_context = f"Database matches found: {product_info}"

    client = get_openai_client()
    if client is None:
        return fallback_product_reply(user_message, product_context)

    prompt = f"""
    You are the Vasu Store customer assistant.
    Product Context: {product_context}
    Customer Query: {user_message}

    Rules:
    1. Always reply in English.
    2. Keep the response concise and friendly.
    3. If matching products exist, mention that the user can review the product cards below.
    4. If no products match, suggest searching by product name, category, color, or brand.
    """

    try:
        response = client.responses.create(
            model=getattr(settings, 'OPENAI_CHAT_MODEL', ''),
            input=prompt,
        )
        output_text = getattr(response, 'output_text', '').strip()
        if output_text:
            return output_text
    except Exception as exc:  # pragma: no cover - network/service behavior
        print("AI Error:", exc)

    return fallback_product_reply(user_message, product_context)


ai_reply = safe_ai_reply
