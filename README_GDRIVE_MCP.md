# Sara Slack Bot - Google Drive MCP Integration

This document explains how Sara's Google Drive MCP (Model Context Protocol) integration works and how to use it.

## Overview

Sara can now lookup data in Google Sheets and respond with natural language summaries. The integration uses:

- **MCP Google Drive Server**: Handles authentication and API calls to Google Drive/Sheets
- **Intent Classification**: Automatically detects when users want to lookup sheet data
- **Natural Language Processing**: Converts raw sheet data into conversational responses

## Architecture

```
Slack User → Sara Bot → Intent Classifier → Sheets Service → MCP Client → Google Drive MCP Server → Google Sheets API
```

### Key Components

1. **`orchestrator.py`**: Main bot logic with intent routing
2. **`intent_classifier.py`**: Classifies user intents including `lookup_sheets`
3. **`sheets_service.py`**: High-level service for sheet operations
4. **`mcp_client.py`**: Low-level MCP protocol client
5. **`mcp-gdrive/`**: Google Drive MCP server implementation

## Features

### Supported Queries

Sara can handle various types of sheet lookup requests:

- **General data queries**: "What's in the sales data?"
- **Specific metrics**: "Show me Q4 numbers"
- **Customer information**: "Look up customer data"
- **Direct sheet access**: "Check this spreadsheet: [URL or ID]"

### Natural Language Responses

Sara converts raw spreadsheet data into conversational responses:

- Summarizes key information
- Answers specific questions about the data
- Explains what data is available if the query doesn't match

## Setup and Configuration

### Prerequisites

1. **Node.js** (v16 or higher)
2. **Google Cloud Project** with Sheets API enabled
3. **OAuth 2.0 credentials** for Google Drive access

### Installation

1. **Install MCP server dependencies**:
   ```bash
   cd mcp-gdrive
   npm install
   npm run build
   ```

2. **Configure Google OAuth**:
   - Ensure `mcp-gdrive/gcp-oauth.keys.json` contains your OAuth credentials
   - Update `mcp-gdrive/.env` with correct client ID and secret

3. **Run setup verification**:
   ```bash
   python3 setup_gdrive_mcp.py
   ```

### Authentication

The first time Sara accesses Google Sheets, you'll need to complete OAuth authentication:

1. Sara will start the MCP server
2. Follow the OAuth flow in your browser
3. Grant permissions to access Google Drive
4. Credentials are saved for future use

## Usage Examples

### Basic Queries

```
@Sara what's in the sales spreadsheet?
@Sara show me the latest metrics
@Sara lookup customer information
```

### With Specific Sheet URLs

```
@Sara check this sheet: https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit
@Sara analyze the data in spreadsheet 1ABC...XYZ
```

### Follow-up Questions

```
User: @Sara what's in the Q4 data?
Sara: I found Q4 sales data with revenue of $50K across 3 regions...
User: What about Q3?
Sara: [Analyzes the same or related sheet for Q3 data]
```

## Technical Details

### MCP Protocol

The integration uses the Model Context Protocol (MCP) for structured communication:

- **Tools**: `gdrive_search`, `gsheets_read`, `gsheets_update_cell`
- **Resources**: Direct access to Google Drive files
- **Authentication**: OAuth 2.0 with token refresh

### Error Handling

Sara gracefully handles various error scenarios:

- **Authentication failures**: Prompts for re-authentication
- **Sheet not found**: Suggests alternative searches
- **Permission errors**: Explains access requirements
- **Network issues**: Provides helpful error messages

### Performance

- **Async operations**: Non-blocking sheet access
- **Connection reuse**: MCP server stays running between requests
- **Caching**: OAuth tokens are cached for efficiency

## Troubleshooting

### Common Issues

1. **"Couldn't connect to Google Drive"**
   - Check if MCP server is built: `cd mcp-gdrive && npm run build`
   - Verify OAuth credentials in `gcp-oauth.keys.json`

2. **"Sheet not found or not accessible"**
   - Ensure the sheet is shared with your Google account
   - Check if the spreadsheet ID is correct

3. **Authentication loops**
   - Clear cached tokens: `rm mcp-gdrive/token.json`
   - Re-run authentication flow

### Debug Mode

Enable debug logging by setting environment variables:

```bash
export DEBUG=mcp:*
python3 orchestrator.py
```

## Security Considerations

- **OAuth tokens** are stored locally in `mcp-gdrive/token.json`
- **API credentials** should be kept secure in `.env` files
- **Sheet access** is limited to the authenticated user's permissions
- **No data persistence**: Sara doesn't store sheet data permanently

## Extending the Integration

### Adding New Sheet Operations

1. **Add new tools** to the MCP server in `mcp-gdrive/tools/`
2. **Update the client** in `mcp_client.py` to support new operations
3. **Extend the service** in `sheets_service.py` for higher-level functions
4. **Update intent classification** to recognize new query types

### Custom Response Formatting

Modify the `generate_natural_response()` function in `sheets_service.py` to:

- Add custom formatting for specific data types
- Include charts or visualizations
- Support different response styles

## API Reference

### SheetsService Methods

- `lookup_data_in_sheets(query: str) -> str`: Main lookup function
- `extract_spreadsheet_id(text: str) -> Optional[str]`: Extract sheet ID from text
- `generate_natural_response(query: str, data: str) -> str`: Generate response

### MCPClient Methods

- `search_sheets(query: str) -> Optional[str]`: Search for sheets
- `read_sheet_data(id: str, ranges: List[str]) -> Optional[str]`: Read sheet data
- `call_tool(name: str, args: Dict) -> Optional[Dict]`: Generic tool calling

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review MCP server logs in the terminal
3. Verify Google Cloud Console settings
4. Test with the setup script: `python3 setup_gdrive_mcp.py`
