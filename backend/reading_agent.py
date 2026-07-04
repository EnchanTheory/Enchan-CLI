import json
from pathlib import Path
from typing import Optional

# document types
DOC_SOURCE_CODE = "source_code"
DOC_NOVEL = "novel_or_story"
DOC_PAPER = "paper_or_research_note"
DOC_LOG = "log_or_session"
DOC_GENERIC = "generic_text"

# intents
INTENT_SUMMARY = "overall_summary"
INTENT_QUESTION = "specific_question"
INTENT_IMPLEMENTATION = "implementation_explanation"
INTENT_BUG = "bug_or_error_analysis"
INTENT_EVIDENCE = "evidence_extraction"

def classify_document(text: str, path: str, model=None, tokenizer=None) -> str:
    ext = Path(path).suffix.lower()
    
    if ext in {".py", ".js", ".ts", ".jsx", ".tsx", ".cpp", ".c", ".h", ".cs", ".java", ".go", ".rs", ".php", ".rb"}:
        return DOC_SOURCE_CODE
        
    if ext in {".log"} or "log" in str(path).lower() or text.startswith("[System]") or "INFO" in text[:500] or "ERROR" in text[:500]:
        return DOC_LOG
        
    if ext in {".pdf", ".tex"}:
        return DOC_PAPER
        
    # For ambiguous text files, use the AI to read a few lines and decide if possible
    if ext in {".txt", ".md", ""} or "abstract" in text[:1000].lower() or "introduction" in text[:1000].lower():
        if model is not None and tokenizer is not None:
            import torch
            print("[Reading Agent] Using AI to read a few lines to determine document type...")
            prompt = (
                f"Read the following excerpt from '{path}' and classify it into EXACTLY ONE of these categories: "
                f"[{DOC_NOVEL}, {DOC_PAPER}, {DOC_GENERIC}]. Return ONLY the category name.\n\n"
                f"Excerpt:\n{text[:1500]}\n\nCategory:"
            )
            chat_history = [{"role": "user", "content": prompt}]
            formatted_prompt = tokenizer.apply_chat_template(chat_history, add_generation_prompt=True, tokenize=False)
            inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=15, do_sample=False, temperature=0.0)
                
            response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            
            for doc_type in {DOC_NOVEL, DOC_PAPER, DOC_GENERIC}:
                if doc_type in response:
                    return doc_type
                    
        # Fallback to heuristics if model isn't available or AI failed to pick a valid category
        markers = ("章", "序章", "第一章", "第二章", "第三章", "登場人物", "あらすじ", "Chapter", "Prologue")
        if any(marker in text[:20000] for marker in markers):
            return DOC_NOVEL
        if "abstract" in text[:1000].lower() or "introduction" in text[:1000].lower():
            return DOC_PAPER
            
    return DOC_GENERIC

def classify_intent(query: str) -> str:
    q = query.lower()
    
    if any(m in q for m in ["内容", "あらすじ", "物語", "全体", "概要", "要約", "流れ", "summary", "summarize", "overview", "plot", "story"]):
        return INTENT_SUMMARY
        
    if any(m in q for m in ["実装", "コード", "仕組み", "how it works", "implementation", "explain code"]):
        return INTENT_IMPLEMENTATION
        
    if any(m in q for m in ["エラー", "バグ", "原因", "error", "bug", "fail", "exception"]):
        return INTENT_BUG
        
    if any(m in q for m in ["どこ", "証拠", "見つけて", "find", "evidence", "where", "search"]):
        return INTENT_EVIDENCE
        
    return INTENT_QUESTION

def plan_retrieval(document_type: str, intent: str) -> dict:
    plan = {
        "budget": 8,
        "story_summary_mode": False,
        "preserve_structure": False,
    }
    
    if document_type == DOC_NOVEL and intent == INTENT_SUMMARY:
        plan["story_summary_mode"] = True
        plan["budget"] = 8
        
    elif document_type == DOC_SOURCE_CODE:
        plan["preserve_structure"] = True
        if intent == INTENT_IMPLEMENTATION:
            plan["budget"] = 10
        elif intent == INTENT_BUG:
            plan["budget"] = 6
            
    elif document_type == DOC_LOG:
        if intent == INTENT_BUG:
            plan["budget"] = 10
            
    return plan

def run_retrieval(plan: dict, query: str, text: str, tokenizer, source_tokens: int) -> str:
    from backend.context_compression import compress_context
    return compress_context(
        query=query, 
        large_text=text, 
        budget=plan["budget"], 
        tokenizer=tokenizer, 
        source_tokens=source_tokens,
        force_story_mode=plan.get("story_summary_mode", False)
    )

def build_prompt(plan: dict, compressed_context: str, user_query: str) -> str:
    # Future extension point for injecting system instructions based on the plan
    return compressed_context

def execute_reading_pipeline(text: str, path: str, query: str, tokenizer, source_tokens: int, model=None) -> tuple[str, dict]:
    doc_type = classify_document(text, path, model=model, tokenizer=tokenizer)
    intent = classify_intent(query)
    plan = plan_retrieval(doc_type, intent)
    
    print(f"\n[Reading Agent] Document Type: {doc_type}")
    print(f"[Reading Agent] Intent: {intent}")
    print(f"[Reading Agent] Retrieval Plan: {json.dumps(plan)}")
    
    compressed = run_retrieval(plan, query, text, tokenizer, source_tokens)
    final_text = build_prompt(plan, compressed, query)
    
    return final_text, {"doc_type": doc_type, "intent": intent, "plan": plan}
