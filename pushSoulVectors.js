
// pushSoulVectors.js

const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

async function pushSoulVectors() {
  // 1) Load service account credentials from environment variable or file
  // Option A: from an env var (recommended on Render)
  const creds = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON);
  // Option B: from a local file (for local testing)
  //const creds = JSON.parse(fs.readFileSync(path.join(__dirname, 'service-account.json'), 'utf8'));

  // 2) Set up Google Auth client
  const auth = new google.auth.GoogleAuth({
    credentials: creds,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });

  // 3) Create Sheets API client
  const sheets = google.sheets({ version: 'v4', auth });

  // 4) Load the latest soul_with_vectors.json
  const soulPath = path.join(__dirname, 'soul_with_vectors.json');
  if (!fs.existsSync(soulPath)) {
    throw new Error(`Cannot find ${soulPath}`);
  }
  const soulData = JSON.parse(fs.readFileSync(soulPath, 'utf8'));
  if (!Array.isArray(soulData) || soulData.length === 0) {
    throw new Error('soul_with_vectors.json is empty or not an array');
  }

  // 5) Prepare header row & data rows
  const headers = Object.keys(soulData[0]);
  const rows = soulData.map(obj =>
    headers.map(h =>
      h === 'vector'
        ? JSON.stringify(obj.vector)         // stringified array
        : obj[h] != null
          ? String(obj[h])
          : ''
    )
  );

  // 6) Clear existing sheet contents
  const spreadsheetId = '1gUJhD58t0_RxLVmzi4f3cLCCoC3ggXwR31F0hQlhBhU';
  const sheetName = 'Soul Vectors';
  await sheets.spreadsheets.values.clear({
    spreadsheetId,
    range: sheetName,
  });

  // 7) Write headers + rows back
  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: `${sheetName}!A1`,
    valueInputOption: 'RAW',
    requestBody: {
      values: [headers, ...rows],
    },
  });

  console.log(`✅ Updated "${sheetName}" with ${rows.length} rows.`);
}

// Execute the function
pushSoulVectors().catch(err => {
  console.error('🚨 Error updating soul vectors:', err);
  process.exit(1);
});
