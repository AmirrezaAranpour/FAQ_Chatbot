// Lightweight, safe Markdown renderer for the chat UI.
// - Escapes HTML first
// - Supports headings (#..######), bullet lists (- item), **bold**, and `code`
// - Keeps UI clean by not showing raw Markdown markers like '##'

function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function inlineMd(s) {
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); // bold
  s = s.replace(/`(.+?)`/g, "<code>$1</code>");          // inline code
  return s;
}

function mdToHtml(md) {
  const lines = escapeHtml(md).split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();

    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      closeList();
      const level = h[1].length;
      html += `<div class="md-h md-h${level}">${inlineMd(h[2])}</div>`;
      continue;
    }

    const li = line.match(/^-+\s+(.*)$/);
    if (li) {
      if (!inList) {
        html += "<ul class='md-ul'>";
        inList = true;
      }
      html += `<li>${inlineMd(li[1])}</li>`;
      continue;
    }

    if (!line) {
      closeList();
      html += "<div class='md-spacer'></div>";
      continue;
    }

    closeList();

    if (line.toLowerCase().startsWith("sources:")) {
      html += `<div class="md-sources">${inlineMd(line)}</div>`;
    } else {
      html += `<div class="md-p">${inlineMd(line)}</div>`;
    }
  }

  closeList();
  return html;
}
