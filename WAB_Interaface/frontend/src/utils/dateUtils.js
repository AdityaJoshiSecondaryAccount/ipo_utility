/**
 * Formats ISO timestamps accurately to real-world local time.
 */

export function parseUTCDate(dateVal) {
  if (!dateVal) return new Date();
  if (dateVal instanceof Date) return dateVal;
  
  let str = String(dateVal).trim();
  // If no timezone indicator (no Z, no +, no -offset after time), append 'Z' so JS treats as UTC
  if (!str.endsWith('Z') && !str.includes('+') && !/T.*\d{2}-\d{2}/.test(str)) {
    str += 'Z';
  }
  const d = new Date(str);
  return isNaN(d.getTime()) ? new Date() : d;
}

export function formatConversationTime(dateVal) {
  if (!dateVal) return '';
  const date = parseUTCDate(dateVal);
  const now = new Date();

  const isToday = date.toDateString() === now.toDateString();
  if (isToday) {
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
  }

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }

  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export function formatMessageTime(dateVal) {
  if (!dateVal) return '';
  const date = parseUTCDate(dateVal);
  const now = new Date();
  
  const timeStr = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
  
  if (date.toDateString() === now.toDateString()) {
    return timeStr;
  }
  
  const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  return `${dateStr}, ${timeStr}`;
}

export function getBadgeDateString(dateVal) {
  if (!dateVal) return '';
  const date = parseUTCDate(dateVal);
  const now = new Date();
  
  if (date.toDateString() === now.toDateString()) {
    return 'Today';
  }
  
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }
  
  return date.toLocaleDateString([], { year: 'numeric', month: 'long', day: 'numeric' });
}
