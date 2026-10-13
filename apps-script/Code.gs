/**
 * Brokerage Reviews: FxPro commentary feed.
 *
 * Runs inside your own Google account and gives the website's import script
 * read access to emails from ONE sender (FXPRO_SENDER) and nothing else.
 * It can also send one kind of email: a short reply to one of that sender's
 * emails with the link to the published post on SITE_URL (action "replyLink").
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
 *
 * Updating an existing deployment (keeps the same URL and key): paste the new
 * file, Save, then Deploy > Manage deployments > pencil icon > Version: New
 * version > Deploy. Approve any new permission Google asks for.
 */

var FXPRO_SENDER = 'e.kalman@fxpro.com';
var SITE_URL = 'https://brokeragereviews.net/blog/';
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

/**
 * Sending goes through POST so a link preview or crawler can never trigger it.
 * Body (JSON): { key, action: "replyLink", id: <message id>, url: <post url> }
 */
function doPost(e) {
  var p = {};
  try { p = JSON.parse((e && e.postData && e.postData.contents) || '{}'); } catch (err) {}
  var key = PropertiesService.getScriptProperties().getProperty('API_KEY');
  if (!key || p.key !== key) return json_({ error: 'unauthorized' });

  if (p.action === 'replyLink' && p.id && p.url) {
    return json_(replyLink_(p.id, p.url));
  }
  return json_({ error: 'unknown action' });
}

/**
 * Replies to the sender's email with the post link. Only links to a page on
 * SITE_URL are allowed, and it never sends twice for the same link in a thread.
 */
function replyLink_(id, url) {
  var pattern = new RegExp('^' + SITE_URL.replace(/[.\/]/g, '\\$&') + '[a-z0-9-]+\\.html$');
  if (!pattern.test(url)) return { error: 'url not allowed' };
  var message = findMessage_(id);
  if (!message) return { error: 'not found' };

  var thread = message.getThread();
  var me = Session.getEffectiveUser().getEmail().toLowerCase();
  // Earlier replies sent through another tool carry the link wrapped in a
  // google.com redirect; those don't count, so a clean link can still be sent.
  var already = thread.getMessages().filter(function (m) {
    var body = m.getPlainBody();
    return m.getFrom().toLowerCase().indexOf(me) !== -1 && body.indexOf(url) !== -1 &&
        body.indexOf('google.com/url?q=' + url) === -1;
  })[0];
  if (already) return { status: 'already sent', date: already.getDate().toISOString() };

  var name = message.getFrom().replace(/<.*>/, '').replace(/"/g, '').trim().split(/\s+/)[0] || 'there';
  var text = 'Hi ' + name + ',\n\nThanks for this, it\'s now live on the site:\n' + url + '\n\nBest,\nAdrian';
  var html = 'Hi ' + name + ',<br><br>Thanks for this, it&#39;s now live on the site:<br>' +
      '<a href="' + url + '">' + url + '</a><br><br>Best,<br>Adrian';
  message.reply(text, { htmlBody: html });
  return { status: 'sent', date: new Date().toISOString() };
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
