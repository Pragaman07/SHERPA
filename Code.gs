/**
 * SEO Reporting Automation Script
 * 
 * This script fetches data from Google Search Console and Google Analytics 4,
 * generates an AI summary using Google's Gemini API, and updates a Google Slides template.
 */

// ==========================================
// PART 1: CONFIGURATION
// ==========================================
const CONFIG = {
  // GA4 Property ID (e.g., '123456789')
  GA4_PROPERTY_ID: 'YOUR_GA4_PROPERTY_ID',
  
  // GSC Site URL (e.g., 'sc-domain:example.com' or 'https://www.example.com/')
  GSC_SITE_URL: 'YOUR_GSC_SITE_URL',
  
  // Google Slides Template ID (from the URL of your template)
  SLIDE_TEMPLATE_ID: 'YOUR_SLIDE_TEMPLATE_ID',
  
  // Google Drive Folder ID where reports will be saved
  OUTPUT_FOLDER_ID: 'YOUR_OUTPUT_FOLDER_ID',
  
  // Gemini API Key (get from aistudio.google.com)
  GEMINI_API_KEY: 'YOUR_GEMINI_API_KEY',
  
  // Gemini Model to use
  GEMINI_MODEL: 'gemini-1.5-flash'
};

// ==========================================
// PART 2: DATE RANGE HELPER
// ==========================================
/**
 * Calculates the start and end dates for the last full month.
 * @return {Object} {startDate: 'YYYY-MM-DD', endDate: 'YYYY-MM-DD', monthName: 'October'}
 */
function getLastMonthDates() {
  const now = new Date();
  // Go to the first day of the current month
  const firstDayCurrentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  // Subtract one day to get the last day of the previous month
  const lastDayPrevMonth = new Date(firstDayCurrentMonth - 1);
  // Get the first day of the previous month
  const firstDayPrevMonth = new Date(lastDayPrevMonth.getFullYear(), lastDayPrevMonth.getMonth(), 1);

  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  return {
    startDate: formatDate(firstDayPrevMonth),
    endDate: formatDate(lastDayPrevMonth),
    monthName: monthNames[firstDayPrevMonth.getMonth()],
    year: firstDayPrevMonth.getFullYear()
  };
}

// ==========================================
// PART 3: FETCH DATA
// ==========================================

/**
 * Fetches data from Google Search Console.
 * Requires 'Google Search Console API' advanced service enabled.
 */
function getGSCData(startDate, endDate) {
  console.log(`Fetching GSC data for ${CONFIG.GSC_SITE_URL} from ${startDate} to ${endDate}...`);
  
  const request = {
    startDate: startDate,
    endDate: endDate,
    dimensions: ['query'],
    rowLimit: 1 // We only need the top keyword for the specific tag
  };

  // 1. Get Totals (Clicks, Impressions, CTR) - Aggregated
  // We do a separate query without dimensions to get site-wide totals easily, 
  // or we can aggregate from a larger query. 
  // Better approach for totals: Query without dimensions.
  const totalsRequest = {
    startDate: startDate,
    endDate: endDate,
    dimensions: [] // No dimensions = totals
  };
  
  let totalClicks = 0;
  let totalImpressions = 0;
  let ctr = 0;

  try {
    const totalsResponse = SearchConsole.Searchanalytics.query(totalsRequest, CONFIG.GSC_SITE_URL);
    if (totalsResponse.rows && totalsResponse.rows.length > 0) {
      totalClicks = totalsResponse.rows[0].clicks;
      totalImpressions = totalsResponse.rows[0].impressions;
      ctr = (totalsResponse.rows[0].ctr * 100).toFixed(2) + '%';
    }
  } catch (e) {
    console.error('Error fetching GSC totals:', e);
    throw new Error('Failed to fetch GSC Totals. Check Site URL and Permissions.');
  }

  // 2. Get Top Keyword
  let topKeyword = 'N/A';
  try {
    const queryRequest = {
      startDate: startDate,
      endDate: endDate,
      dimensions: ['query'],
      rowLimit: 1,
      orderBy: [{property: 'clicks', sortOrder: 'DESCENDING'}]
    };
    const queryResponse = SearchConsole.Searchanalytics.query(queryRequest, CONFIG.GSC_SITE_URL);
    if (queryResponse.rows && queryResponse.rows.length > 0) {
      topKeyword = queryResponse.rows[0].keys[0];
    }
  } catch (e) {
    console.error('Error fetching GSC top keyword:', e);
  }

  return {
    clicks: totalClicks,
    impressions: totalImpressions,
    ctr: ctr,
    topKeyword: topKeyword
  };
}

/**
 * Fetches data from Google Analytics 4.
 * Requires 'Google Analytics Data API' advanced service enabled.
 */
function getGA4Data(startDate, endDate) {
  console.log(`Fetching GA4 data for property ${CONFIG.GA4_PROPERTY_ID}...`);
  
  try {
    const request = {
      dateRanges: [{ startDate: startDate, endDate: endDate }],
      metrics: [{ name: 'sessions' }],
      dimensionFilter: {
        filter: {
          fieldName: 'sessionDefaultChannelGroup',
          stringFilter: {
            value: 'Organic Search'
          }
        }
      }
    };

    const response = AnalyticsData.Properties.runReport(request, `properties/${CONFIG.GA4_PROPERTY_ID}`);
    
    let organicSessions = 0;
    if (response.rows && response.rows.length > 0) {
      organicSessions = response.rows[0].metricValues[0].value;
    }

    return {
      organicSessions: organicSessions
    };
  } catch (e) {
    console.error('Error fetching GA4 data:', e);
    throw new Error('Failed to fetch GA4 Data. Check Property ID and Permissions.');
  }
}

// ==========================================
// PART 4: AI ANALYSIS (THE BRAIN)
// ==========================================

/**
 * Sends data to Gemini API to generate an executive summary.
 */
function getGeminiSummary(gscData, ga4Data, monthName) {
  console.log('Generating AI summary with Gemini...');
  
  const prompt = `
    You are an SEO Strategist. Analyze the following SEO performance data for ${monthName}:
    
    - Organic Sessions (GA4): ${ga4Data.organicSessions}
    - Total Clicks (GSC): ${gscData.clicks}
    - Total Impressions (GSC): ${gscData.impressions}
    - CTR: ${gscData.ctr}
    - Top Performing Keyword: "${gscData.topKeyword}"
    
    Write a concise 3-bullet point executive summary. 
    The first bullet should highlight a main win. 
    The second bullet should highlight a key observation or area for improvement.
    The third bullet should be a brief strategic recommendation.
    Keep the tone professional and actionable. Do not use markdown formatting like **bold** in the output, just plain text.
  `;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${CONFIG.GEMINI_MODEL}:generateContent?key=${CONFIG.GEMINI_API_KEY}`;
  
  const payload = {
    contents: [{
      parts: [{ text: prompt }]
    }]
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const json = JSON.parse(response.getContentText());
    
    if (json.error) {
      throw new Error(`Gemini API Error: ${json.error.message}`);
    }
    
    // Extract text from response
    const summary = json.candidates[0].content.parts[0].text;
    return summary.trim();
    
  } catch (e) {
    console.error('Error calling Gemini API:', e);
    return "Error generating AI summary. Please check logs.";
  }
}

// ==========================================
// PART 5: REPORT GENERATION
// ==========================================

/**
 * Creates a new slide deck from the template and populates it with data.
 */
function createSlideDeck(data) {
  console.log('Creating slide deck...');
  
  // 1. Copy Template
  const templateFile = DriveApp.getFileById(CONFIG.SLIDE_TEMPLATE_ID);
  const targetFolder = DriveApp.getFolderById(CONFIG.OUTPUT_FOLDER_ID);
  const newFileName = `SEO Report - ${data.monthName} ${data.year}`;
  const newFile = templateFile.makeCopy(newFileName, targetFolder);
  
  // 2. Open new presentation
  const presentation = SlidesApp.openById(newFile.getId());
  
  // 3. Perform replacements
  // We replace text in all slides.
  // Note: replaceAllText returns the number of occurrences changed.
  
  presentation.replaceAllText('{{Month}}', data.monthName);
  presentation.replaceAllText('{{Year}}', data.year.toString());
  presentation.replaceAllText('{{OrganicSessions}}', Number(data.ga4.organicSessions).toLocaleString());
  presentation.replaceAllText('{{TotalClicks}}', Number(data.gsc.clicks).toLocaleString());
  presentation.replaceAllText('{{TotalImpressions}}', Number(data.gsc.impressions).toLocaleString());
  presentation.replaceAllText('{{CTR}}', data.gsc.ctr);
  presentation.replaceAllText('{{TopKeyword}}', data.gsc.topKeyword);
  presentation.replaceAllText('{{AISummary}}', data.aiSummary);
  
  presentation.saveAndClose();
  
  return newFile.getUrl();
}

// ==========================================
// PART 6: MAIN EXECUTION
// ==========================================

function runMonthlyReport() {
  const ui = SpreadsheetApp.getActiveSpreadsheet() ? SpreadsheetApp.getUi() : null; // Handle if running from Sheets or standalone
  
  try {
    // 1. Get Dates
    const dateRange = getLastMonthDates();
    console.log(`Running report for: ${dateRange.monthName} ${dateRange.year}`);
    
    // 2. Fetch Data
    const gscData = getGSCData(dateRange.startDate, dateRange.endDate);
    const ga4Data = getGA4Data(dateRange.startDate, dateRange.endDate);
    
    // 3. AI Analysis
    const aiSummary = getGeminiSummary(gscData, ga4Data, dateRange.monthName);
    
    // 4. Create Slides
    const reportData = {
      monthName: dateRange.monthName,
      year: dateRange.year,
      gsc: gscData,
      ga4: ga4Data,
      aiSummary: aiSummary
    };
    
    const reportUrl = createSlideDeck(reportData);
    
    console.log('SUCCESS! Report generated:', reportUrl);
    if (ui) ui.alert('Success', `Report generated: ${reportUrl}`, ui.ButtonSet.OK);
    
  } catch (e) {
    console.error('FAILED to run report:', e);
    if (ui) ui.alert('Error', `Failed: ${e.message}`, ui.ButtonSet.OK);
  }
}
