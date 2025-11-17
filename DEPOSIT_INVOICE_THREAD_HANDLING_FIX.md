# Deposit Invoice Thread Handling Fix - Complete

## Problem Statement

The deposit invoice generation flow was not working correctly in threads. After fetching brand details and saying "INVOICE", users would be prompted for amount (which worked), but when they sent the invoice number, the system would route back to the old intent handling flow instead of continuing the multi-step invoice generation process.

## Root Cause Analysis

The issue was that the deposit invoice service (`deposit_invoice_service_v2.py`) was **stateless** - it didn't track where the user was in the multi-step flow. Every time a new message came in:

1. The orchestrator would re-classify the intent based on combined text (parent + current message)
2. Even though the user was expected to provide an invoice number, the system would treat "INV-001" as a new generic message
3. Intent classification would route it incorrectly instead of continuing the invoice flow

This contrasted with `brand_info_service.py`, which successfully used `pending_confirmations` to track state.

## Solution Implementation

### 1. Added State Management to `deposit_invoice_service_v2.py`

**New state tracking variables:**
```python
deposit_invoice_threads = {}  # thread_id -> {"stage": "awaiting_amount|awaiting_invoice_number", "brand_data": {...}, "amount": "..."}
```

**New helper functions:**
- `is_in_deposit_invoice_flow(thread_id)` - Check if thread is in active flow
- `get_deposit_invoice_state(thread_id)` - Get current flow state
- `set_deposit_invoice_state(thread_id, stage, brand_data, amount)` - Set flow state
- `clear_deposit_invoice_state(thread_id)` - Remove flow state

### 2. Updated `handle_deposit_invoice()` Function

The function now handles multi-step flows:

**Stage 1: Initial Request**
- User says "INVOICE" with brand data cached
- Missing amount and invoice number
- Sets state to `awaiting_amount`
- Prompts: "Please provide the deposit amount"

**Stage 2: Amount Provided**
- User sends "50000"
- Extracts amount, stores it
- Updates state to `awaiting_invoice_number`
- Prompts: "Great! Now please provide the invoice number"

**Stage 3: Invoice Number Provided**
- User sends "INV-001"
- Extracts invoice number
- Combines with stored amount and brand data
- Generates and uploads invoice
- Clears state

**Key Logic:**
```python
if existing_state:
    stage = existing_state.get("stage")
    
    if stage == "awaiting_amount":
        # Extract and store amount, move to next stage
        ...
    elif stage == "awaiting_invoice_number":
        # Extract invoice number, generate invoice
        ...
```

### 3. Updated `orchestrator.py` Thread Handler

**CRITICAL FIX:** Check for deposit invoice flow state BEFORE intent classification:

```python
# Check if we're in an active deposit invoice flow BEFORE intent classification
if is_in_deposit_invoice_flow(thread_ts):
    print(f"📨 [THREAD] Thread is in active deposit invoice flow - bypassing intent classification")
    
    # Route directly to deposit invoice handler with user text only
    handle_deposit_invoice({**event, "text": user_text}, say, brand_data=brand_data)
    return
```

This ensures that when a user is expected to provide amount or invoice number, the message is routed directly to the deposit invoice handler without going through intent classification.

## Flow Diagram

```
User: @Sara fetch Freakins info
  ↓
Sara: [Shows brand information, caches data]
  ↓
User: INVOICE
  ↓
Sara: Sets state → awaiting_amount
      Prompts: "Please provide the deposit amount"
  ↓
User: 50000
  ↓
[CRITICAL: is_in_deposit_invoice_flow() returns True]
  ↓
Sara: Extracts amount, updates state → awaiting_invoice_number
      Prompts: "Now please provide the invoice number"
  ↓
User: INV-001
  ↓
[CRITICAL: is_in_deposit_invoice_flow() returns True]
  ↓
Sara: Extracts invoice number
      Combines with cached data
      Generates invoice
      Clears state
      Uploads invoice PDF
```

## Benefits

1. **State Persistence**: The flow remembers where the user is in the process
2. **Intent Bypass**: When in a flow, user input is treated as expected data, not subject to re-classification
3. **Clear Prompts**: User knows exactly what to provide at each step
4. **Error Handling**: If extraction fails, user gets clear feedback
5. **Flexible Entry**: Can handle all-in-one requests or step-by-step

## Testing Recommendations

Test the following scenarios:

1. **Basic Flow:**
   - Fetch brand info → Say "INVOICE" → Provide amount → Provide invoice number

2. **All-in-One:**
   - "generate invoice INV-001 for 50000" (with brand data cached)

3. **Error Recovery:**
   - Provide invalid amount ("abc") → Should prompt again
   - Provide invalid invoice format → Should prompt again

4. **State Management:**
   - Start invoice flow → Let it time out naturally
   - Start multiple invoice flows in different threads simultaneously

## Files Modified

1. `deposit_invoice_service_v2.py` - Added state management and multi-step flow handling
2. `orchestrator.py` - Added state check before intent classification in thread handler

## Deployment Notes

- No database changes required (state stored in memory)
- No new dependencies
- Compatible with existing deposit invoice functionality
- State is per-thread, so multiple threads can have independent flows

## Future Enhancements

1. Add timeout mechanism to clear stale states
2. Add state persistence to database for long-running processes
3. Add "cancel" command to exit flow early
4. Add confirmation step before generating invoice

---

**Status**: ✅ COMPLETE  
**Date**: 17/11/2025  
**Priority**: HIGH - Fixes critical user flow issue
