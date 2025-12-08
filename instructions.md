# Google Apps Script Setup Instructions

To run the SEO Reporting script, you must enable the following "Advanced Services" in the Google Apps Script editor.

## Required Services

1.  **Google Analytics Data API**
    *   **Identifier:** `AnalyticsData`
    *   **Why:** To fetch organic session data from GA4.

2.  **Google Search Console API**
    *   **Identifier:** `SearchConsole`
    *   **Why:** To fetch clicks, impressions, CTR, and keyword data.

3.  **Google Slides API**
    *   **Identifier:** `SlidesApp` (Built-in service, but `Slides` advanced service is sometimes needed for complex operations. For this script, the built-in `SlidesApp` class is used, but if you encounter errors, enable the **Google Slides API** advanced service as `Slides`).
    *   *Note: The script uses `SlidesApp` which is a built-in service, but ensuring the API is enabled in the Cloud Project (which happens automatically when adding the Advanced Service) is good practice.*

## How to Enable Services

1.  Open your Google Apps Script project.
2.  In the left sidebar, click the **Editor** icon `< >`.
3.  On the left, next to **Services**, click the **+ (Add a service)** button.
4.  Scroll down or search for **"Google Analytics Data API"**.
5.  Select it and click **Add**. Ensure the identifier is `AnalyticsData`.
6.  Repeat the process for **"Google Search Console API"** (Identifier: `SearchConsole`).

## API Key & IDs

Remember to fill in the `CONFIG` object at the top of `Code.gs` with your specific details:
*   `GA4_PROPERTY_ID`: Found in GA4 Admin > Property Settings.
*   `GSC_SITE_URL`: Found in GSC property selector (ensure it matches exactly, e.g., `sc-domain:example.com`).
*   `SLIDE_TEMPLATE_ID`: The long string in your Google Slides URL between `/d/` and `/edit`.
*   `OUTPUT_FOLDER_ID`: The long string in your Google Drive Folder URL.
*   `GEMINI_API_KEY`: Generate this at [aistudio.google.com](https://aistudio.google.com/).
