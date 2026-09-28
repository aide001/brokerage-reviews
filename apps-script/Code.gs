/**
 * Brokerage Reviews: FxPro commentary feed.
 *
 * Runs inside your own Google account and gives the website's import script
 * read access to emails from ONE sender (FXPRO_SENDER) and nothing else.
 * Every request must carry the secret key created by setup().
 *
 * Setup (one time):
 *   1. Go to script.google.com, click New project, and paste this file in
 *      place of the example code. Save.
 *   2. Choose "setup" in the function menu at the top and click Run.
 *      Approve the permissions when asked. Then open "Execution log" and
 *      copy the key it prints.
 *   3. Click Deploy > New deployment > type "Web app".
 *      Execute as: Me. Who has access: Anyone. Click Deploy and copy the
 *      Web app URL.
 *   4. Store the URL as FXPRO_SCRIPT_URL and the key as FXPRO_SCRIPT_KEY in
 *      the Claude environment settings (never in the website's code).
 */

var FXPRO_SENDER = 'e.kalman@fxpro.com';
var MAX_LIMIT = 20;

function setup() {
  var props = PropertiesService.getScriptProperties();
  var key = props.getProperty('API_KEY');
  if (!key) {
    key = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('API_KEY', key);
  }
  // Touch Gmail once so the permission prompt appears during setup.
  GmailApp.search('from:' + FXPRO_SENDER, 0, 1);
  Logger.log('Your FXPRO_SCRIPT_KEY is: ' + key);
}

/** Creates a new key, which stops the old one from working. */
function rotateKey() {
  PropertiesService.getScriptProperties().deleteProperty('API_KEY');
  setup();
}

function doGet(e) {
  var p = (e && e.parameter) || {};
  var key = PropertiesService.getScriptProperties().getProperty('API_KEY');
  if (!key || p.key !== key) return json_({ error: 'unauthorized' });

  if (p.action === 'list') {
    var limit = Math.min(parseInt(p.limit, 10) || 5, MAX_LIMIT);
    return json_({ messages: listMessages_(limit) });
  }
  if (p.action === 'message' && p.id) {
    var message = findMessage_(p.id);
    if (!message) return json_({ error: 'not found' });
    return json_({ message: describe_(message, true) });
  }
  return json_({ error: 'unknown action' });
}

/** Most recent emails from the sender that have attachments, newest first. */
function listMessages_(limit) {
  var threads = GmailApp.search('from:' + FXPRO_SENDER + ' has:attachment', 0, limit);
  var out = [];
  threads.forEach(function (thread) {
    thread.getMessages().forEach(function (m) {
      if (isFromSender_(m)) out.push(describe_(m, false));
    });
  });
  out.sort(function (a, b) { return b.date < a.date ? -1 : 1; });
  return out.slice(0, limit);
}

function findMessage_(id) {
  try {
    var m = GmailApp.getMessageById(id);
    return m && isFromSender_(m) ? m : null;
  } catch (err) {
    return null;
  }
}

function isFromSender_(m) {
  return m.getFrom().toLowerCase().indexOf(FXPRO_SENDER.toLowerCase()) !== -1;
}

function describe_(m, withFiles) {
  var data = {
    id: m.getId(),
    threadId: m.getThread().getId(),
    subject: m.getSubject(),
    from: m.getFrom(),
    date: m.getDate().toISOString(),
    body: m.getPlainBody(),
    attachments: m.getAttachments().map(function (a) {
      var item = { name: a.getName(), mimeType: a.getContentType(), size: a.getSize() };
      if (withFiles) item.data = Utilities.base64Encode(a.getBytes());
      return item;
    })
  };
  return data;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
