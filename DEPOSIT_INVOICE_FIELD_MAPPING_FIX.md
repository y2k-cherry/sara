# Deposit Invoice Field Mapping Fix - Complete

## Issue Summary
The deposit invoice PDF generator was working properly, but incorrect fields were being populated in the generated invoices. Specifically, the following fields were not being correctly filled:
- Address Line 1
- Address Line 2
- City
- State
- Pin Code
- Phone Number
- Email ID

## Root Cause Analysis

### The Problem
The issue was caused by **incorrect data flow** between two services:

1. **`brand_info_service.py`** was combining all address components into a single comma-separated string in the `get_brand_data_for_invoice()` method
2. **`deposit_invoice_service_v2.py`** was then attempting to parse this combined string back into separate components
3. This parsing logic was flawed and caused incorrect field mapping

### Example of the Problem
For the brand "Off Duty":
- **Input from Google Sheets:**
  - Address Line 1: `09th Floor, Unit No 921, IJMIMA, Malad Link Road`
  - Address Line 2: `Behind Infinti Mall, Marve Road Junction`
  - City: `Mumbai`
  - State: `Maharashtra`
  - Pin Code: `400064`

- **What was happening (INCORRECT):**
  1. brand_info_service combined: `"09th Floor, Unit No 921, IJMIMA, Malad Link Road, Behind Infinti Mall, Marve Road Junction, Mumbai, Maharashtra, 400064"`
  2. deposit_invoice_service tried to split by commas
  3. Fields were incorrectly split due to commas within address components

## Solution Implemented

### Changes Made

#### 1. **brand_info_service.py** (Line ~343-380)
**Changed the `get_brand_data_for_invoice()` method to return separate address components:**

**Before:**
```python
# Combine address fields
address_parts = []
if address_line1:
    address_parts.append(address_line1)
if address_line2:
    address_parts.append(address_line2)
# ... etc
full_address = ", ".join(address_parts)

return {
    'company_name': company_name,
    'address': full_address,  # Combined string
    'phone': phone,
    'email': email
}
```

**After:**
```python
# Keep address components separate
return {
    'company_name': company_name,
    'address_line1': address_line1,  # Separate field
    'address_line2': address_line2,  # Separate field
    'city': city,                    # Separate field
    'state': state,                  # Separate field
    'pin_code': pin_code,           # Separate field
    'phone': phone,
    'email': email
}
```

#### 2. **deposit_invoice_service_v2.py** (Line ~300-345)
**Modified `extract_invoice_fields()` to use separate address components directly:**

**Before:**
```python
if brand_data:
    brand_name = brand_data.get("company_name", "")
    
    # Parse address into components
    address = brand_data.get("address", "")
    address_components = parse_address_components(address, logger)  # Parsing logic
    
    # Use parsed components
    values["Brand_Address_Line_1"] = address_components["Brand_Address_Line_1"]
    # ... etc
```

**After:**
```python
if brand_data:
    brand_name = brand_data.get("company_name", "")
    
    # Use separate address components directly (NO PARSING)
    address_line1 = brand_data.get("address_line1", "")
    address_line2 = brand_data.get("address_line2", "")
    city = brand_data.get("city", "")
    state = brand_data.get("state", "")
    pin_code = brand_data.get("pin_code", "")
    
    # Map directly to template placeholders
    values["Brand_Address_Line_1"] = address_line1
    values["Brand_Address_Line_2"] = address_line2
    values["City"] = city
    values["State"] = state
    values["Pin_Code"] = pin_code
```

Also improved email extraction to try multiple column name variations:
```python
email = data_map.get('email', data_map.get('emailid', data_map.get('email id', data_map.get('email address', ''))))
```

## Testing

### Test Results
Created `test_offduty_invoice_fix.py` to verify the fix with real Offduty brand data:

✅ **All Tests Passed:**
```
Test 1 (Offduty Field Mapping): ✅ PASSED
Test 2 (Backwards Compatibility): ✅ PASSED
```

### Verified Fields for "Off Duty" Brand:
- ✅ Brand Name: `Off Duty`
- ✅ Address Line 1: `09th Floor, Unit No 921, IJMIMA, Malad Link Road`
- ✅ Address Line 2: `Behind Infinti Mall, Marve Road Junction`
- ✅ City: `Mumbai`
- ✅ State: `Maharashtra`
- ✅ Pin Code: `400064`
- ✅ Phone: `+91 99202 29357`
- ✅ Email: `mihir@offduty.in`

## Impact

### Benefits
1. ✅ **Accurate Field Mapping**: All address components, phone, and email are now correctly populated
2. ✅ **No Parsing Errors**: Eliminates the risk of incorrect splitting due to commas in address components
3. ✅ **Better Performance**: Removes unnecessary parsing logic
4. ✅ **Maintainability**: Clearer data flow between services
5. ✅ **Backwards Compatibility**: Still works when no brand data is provided

### Files Modified
1. `brand_info_service.py` - Modified `get_brand_data_for_invoice()` method
2. `deposit_invoice_service_v2.py` - Modified `extract_invoice_fields()` function

### Test File Added
- `test_offduty_invoice_fix.py` - Comprehensive test suite for the fix

## Deployment Notes

### Prerequisites
- No additional dependencies required
- Changes are backward compatible

### Deployment Steps
1. Deploy the updated `brand_info_service.py`
2. Deploy the updated `deposit_invoice_service_v2.py`
3. No database migrations needed
4. No configuration changes needed

### Rollback Plan
If issues occur, revert both files to previous versions simultaneously to maintain compatibility.

## Verification

To verify the fix in production:
1. Fetch brand info for any brand (e.g., "fetch Off Duty info")
2. Generate a deposit invoice for that brand
3. Check the generated PDF/DOCX to ensure all fields are correctly populated:
   - Address Line 1 and 2 should be on separate lines
   - City, State, and Pin Code should be separate
   - Phone and Email should be present

## Conclusion

The field mapping issue has been completely resolved. The deposit invoice generator now correctly populates all address components, phone numbers, and email addresses by receiving them as separate fields from the brand information service, eliminating the error-prone parsing logic.

---

**Fix Date**: November 18, 2025  
**Status**: ✅ Complete and Tested  
**Tested With**: Off Duty brand data  
**Test Results**: All tests passing
