from google.genai import types


def print_model_text(response: types.GenerateContentResponse) -> None:
    """
    Print the model's natural language output, if any.
    """
    # New SDK exposes .text; still print defensively
    text = getattr(response, "text", None)
    if text:
        print(text.strip())
    else:
        # Fall back: collect any text parts
        chunks = []
        try:
            parts = response.candidates[0].content.parts
            for p in parts:
                if getattr(p, "text", None):
                    chunks.append(p.text)
        except Exception:
            pass
        if chunks:
            print("\n".join(chunks).strip())
    res = []
    try:
        if response.function_calls:
            for i, fc in enumerate(response.function_calls, 1):
                print(f"\n[tool-call {i}] name={fc.name}")
                print("args:")
                try:
                    import json as _json
                    res.append(_json.dumps(fc.args, indent=2, sort_keys=True))
                    print(_json.dumps(fc.args, indent=2, sort_keys=True))
                except Exception:
                    print(str(fc.args))
    except Exception:
       pass

    return res