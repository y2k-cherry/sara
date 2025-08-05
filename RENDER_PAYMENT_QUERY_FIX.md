# Fix for "Who Hasn't Paid" Query on Render

## Issue Identified ✅

The "who hasn't paid" query is **working correctly locally** but failing on Render due to missing environment variables.

### Local Test Results
- ✅ Payment query detection: Working
- ✅ Brand Balances sheet access: Working  
- ✅ Data parsing: Working
- ✅ Results: 26 brands with ₹186,087 total outstanding

### Root Cause
The Render deployment is missing the `GOOGLE_API_KEY` environment variable needed to access Google Sheets.

## Fix Required on Render Dashboard 🔧

### Step 1: Add Environment Variable
1. Go to your Render dashboard
2. Navigate to your Sara service
3. Go to **Environment** tab
4. Add new environment variable:
   - **Key**: `GOOGLE_API_KEY`
   - **Value**: `AIzaSyBchp-hY3Sy5PPU1KBax-cdjMx0QjZpocM`

### Step 2: Redeploy
1. After adding the environment variable, Render will automatically redeploy
2. Wait for deployment to complete

## Expected Results After Fix ✅

When you ask "who hasn't paid", Sara should respond with:

```
💸 **Brands that haven't paid** (26 total):

• **HYPHEN**: ₹48,095.00 due
• **Offduty**: ₹24,473.00 due
• **Typsy Beauty**: ₹24,060.00 due
• **Inde Wild**: ₹18,130.00 due
• **mCaffeine**: ₹17,458.00 due
[... and 21 more brands]

💰 **Total outstanding**: ₹186,087.00
```

## Technical Details 🔍

### What's Working
- Intent classification correctly identifies payment queries
- Direct sheets service properly routes to Brand Balances sheet
- OAuth credentials are loaded correctly
- Sheet data parsing and negative balance detection works

### What Was Missing
- `GOOGLE_API_KEY` environment variable on Render
- This key is needed for accessing the Brand Balances Google Sheet

### Code Flow
1. User asks "who hasn't paid"
2. Intent classifier detects `lookup_sheets` intent
3. Orchestrator calls `direct_sheets.process_sheets_query("", query)`
4. DirectSheetsService detects payment query pattern
5. Calls `_check_brand_balances()` method
6. Accesses hardcoded Brand Balances sheet: `1Ch6NflcXS6BfK0zZ8SoeoiU_PwKe8_oEVjDX2tTE8QY`
7. Parses data and finds brands with negative balances
8. Returns formatted response

## Verification ✅

After adding the environment variable, test with:
- "who hasn't paid"
- "unpaid brands" 
- "brands with negative balance"

All should return the same detailed payment status report.
