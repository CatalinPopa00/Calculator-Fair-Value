import re

with open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update instructions to explicitly mention estimates
old_instruction_4 = "4. **Earnings Estimates & CAGR:** If the user asks about earnings estimates on multiple years, you must read the earnings estimates (from Yahoo Finance or other sources) for those specific years, list the EPS estimates explicitly, and ALWAYS automatically calculate the Compound Annual Growth Rate (CAGR) between those years to show the growth trajectory. NEVER say you do not have direct access to Yahoo Finance. The estimates and financial data provided in your context ARE the exact official figures extracted directly from Yahoo Finance in real-time."
new_instruction_4 = "4. **Earnings & Revenue Estimates & CAGR:** If the user asks about EPS or Revenue estimates on multiple years, you MUST read the `Estimates` context block which contains exact EPS and Revenue estimates from Yahoo/Nasdaq for the next 2-3 years. List them explicitly, and ALWAYS automatically calculate the Compound Annual Growth Rate (CAGR) to show the growth trajectory. NEVER say you do not know the estimates without checking the `Estimates` context."

content = content.replace(old_instruction_4, new_instruction_4)

old_instruction_6 = "6. **KNOWLEDGE CUTOFF OVERRIDE & SEARCH:** You MUST IGNORE your internal 'Cutting Knowledge Date'. You DO have access to real-time data through the LIVE RESEARCH DATA block. If the local context does not have the exact numbers the user asks for (e.g., last 4 quarters EPS, specific estimates), you MUST read the LIVE RESEARCH DATA. NEVER say your knowledge is limited or that you don't have the data without checking the LIVE RESEARCH DATA."
new_instruction_6 = "6. **KNOWLEDGE CUTOFF OVERRIDE & SEC REPORTS SEARCH:** You MUST IGNORE your internal 'Cutting Knowledge Date'. If the user asks for data from a specific past year (e.g., 2023 SEC 10-K, 2023 Revenue) or specific historical earnings transcripts that are NOT in the local context, YOU MUST USE YOUR SEARCH TOOL (if available) to search the web (e.g. 'MSFT 2023 10-K' or 'MSFT Q3 2023 transcript') and extract the exact numbers! NEVER say you don't have access to past reports."

content = content.replace(old_instruction_6, new_instruction_6)

# 2. Swap the execution order of Groq and Gemini in Phase 2 so Gemini is PRIMARY.
# This is because Gemini has native google_search tool which solves the user's main complaint.

# We will locate the Phase 2 block:
phase2_start = "    # MULTI-MODEL PIPELINE: Phase 2"

if phase2_start in content:
    # We will just rewrite the execution block from Phase 2 down to OpenAI fallback
    # Since it's a bit complex to regex, I'll use a careful string replace.
    pass

# Actually, an easier way is to just write a replacement for the whole block from Phase 2 onwards
import ast
# Let's replace the whole section starting from `# MULTI-MODEL PIPELINE: Phase 2 (Groq Analyst)`
# down to `if result_content:`

old_block_start = "    # MULTI-MODEL PIPELINE: Phase 2 (Groq Analyst)"
old_block_end = "    if result_content:\n        return result_content"

start_idx = content.find(old_block_start)
end_idx = content.find(old_block_end)

if start_idx != -1 and end_idx != -1:
    old_block = content[start_idx:end_idx]
    
    new_block = """    # MULTI-MODEL PIPELINE: Phase 2 (Gemini Primary with Native Search)
    # We prioritize Gemini because it has the google_search tool native, which solves the user's issue with "AI doesn't know how to search".
    if gemini_key:
        try:
            gemini_messages = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
            gemini_payload = {
                "contents": gemini_messages,
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
                "tools": [{"google_search": {}}]
            }

            chat_models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-flash-lite"
            ]

            import time
            for idx, model in enumerate(chat_models_to_try):
                if result_content:
                    break
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=gemini_payload, timeout=12.0)

                        if resp.status_code == 400 and "tools" in gemini_payload:
                            payload_no_tools = gemini_payload.copy()
                            del payload_no_tools["tools"]
                            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload_no_tools, timeout=8.0)

                        if resp.status_code == 200:
                            data = resp.json()
                            try:
                                result_content = data["candidates"][0]["content"]["parts"][0]["text"]
                                break
                            except (KeyError, IndexError):
                                all_errors.append(f"Gemini {model} Chat missing text parts")
                                break
                        elif resp.status_code == 429:
                            if attempt < max_retries - 1:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                all_errors.append(f"Gemini {model} Chat Rate Limit")
                                if idx < len(chat_models_to_try) - 1:
                                    time.sleep(2)
                        else:
                            error_msg = resp.text[:200]
                            print(f"Gemini Chat Error ({model}): {error_msg}")
                            all_errors.append(f"Gemini {model}({resp.status_code}): {error_msg}")
                            break
                    except Exception as e:
                        print(f"Gemini Chat Exception ({model}): {e}")
                        all_errors.append(f"Gemini {model}: {str(e)}")
                        break

                if result_content:
                    break
        except Exception as e:
            print(f"Gemini Chat Main Exception: {e}")
            all_errors.append(f"Gemini: {str(e)}")

    # Fallback 1: Groq Analyst
    if not result_content and groq_key:
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.5, "max_tokens": 1024},
                    timeout=30
                )
                if resp.status_code == 200:
                    choice = resp.json().get("choices", [{}])[0]
                    result_content = choice.get("message", {}).get("content", "")
                    
                    if choice.get("finish_reason") == "length":
                        print(f"Groq truncated message mid-sentence (hit TPM limits).")
                    break
                elif resp.status_code == 429:
                    print(f"Groq Rate Limit (429) hit in Chat. Attempt {attempt+1}/{max_retries}.")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        error_msg = "429 Rate Limit Exhausted"
                        print(f"Groq Chat Error (status {resp.status_code}): {error_msg}")
                        all_errors.append(f"Groq({resp.status_code}): {error_msg}")
                        break
                else:
                    error_msg = resp.text[:200]
                    print(f"Groq Chat Error (status {resp.status_code}): {error_msg}")
                    all_errors.append(f"Groq({resp.status_code}): {error_msg}")
                    break
            except Exception as e:
                print(f"Groq Chat Exception: {e}")
                all_errors.append(f"Groq: {str(e)}")
                break

    # Fallback 2: OpenAI
    if not result_content and openai_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0.5},
                timeout=30
            )
            if resp.status_code == 200:
                result_content = resp.json()["choices"][0]["message"]["content"]
            else:
                error_msg = resp.text[:200]
                print(f"OpenAI Chat Error (status {resp.status_code}): {error_msg}")
                all_errors.append(f"OpenAI({resp.status_code}): {error_msg}")
        except Exception as e:
            print(f"OpenAI Chat Exception: {e}")
            all_errors.append(f"OpenAI: {str(e)}")\n\n"""

    content = content[:start_idx] + new_block + content[end_idx:]

with open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("api/kpi_audit.py patched successfully")
