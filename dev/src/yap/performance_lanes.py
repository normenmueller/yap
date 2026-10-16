"""Filtered, source-backed activity boards inside performance result cards."""

from html import escape

from . import palette
from .publication_links import activity_pdf


STYLE = palette.css("""
.kr-board .next-marker{grid-area:2/2;align-self:end;justify-self:end;display:flex;align-items:center;justify-content:center;width:14px;height:14px;border:1px solid @namMuted;border-radius:50%;color:@namMuted;font-size:.56rem;line-height:1;font-weight:500}
.kr-board .card-version{margin-left:.35em;font-size:.8em;font-weight:400;color:@namMuted}
.kr-board{max-width:100%;overflow-x:auto;margin-top:18px;padding-bottom:4px;scrollbar-color:@namFrame @namBg}
.kr-board:focus-visible{outline:2px solid @namBrand;outline-offset:4px}
.kr-board-sheet{position:relative;min-width:900px;--kr-rail:28px;color:@namInk;font-size:.76rem;line-height:1.4}
.kr-board-head,.kr-board-row{display:grid;grid-template-columns:var(--kr-remaining,var(--kr-labels)) repeat(var(--status-count,5),minmax(0,1fr))}
.kr-board-head{position:relative;z-index:1;min-height:36px;align-items:center;font-size:.69rem;font-weight:650}
.kr-board-head>div{padding:8px 7px}.kr-board-head .kr-board-status{margin:0 3px;color:var(--kr-status);background:color-mix(in srgb,var(--kr-status) 8%,@namBg);border-radius:5px 5px 0 0}
.kr-board-columns{position:absolute;inset:0 0 0 var(--kr-labels);display:grid;grid-template-columns:repeat(var(--status-count,5),minmax(0,1fr));pointer-events:none;z-index:2}
.kr-board-columns>span{margin:0 3px;border:1px solid color-mix(in srgb,var(--kr-status) 70%,@namLine);border-radius:5px}
.kr-lane{position:relative;display:grid;grid-template-columns:var(--kr-rail) minmax(0,1fr);background:color-mix(in srgb,var(--kr-tone) 7%,@namBg)}
.kr-lane::after,.kr-board-row::after{content:"";position:absolute;inset:3px 4px;border:1px solid @namFrame;border-radius:5px;pointer-events:none}
.kr-lane-category{margin-top:7px}.kr-lane-category::after{border-color:color-mix(in srgb,var(--kr-tone) 55%,@namLine)}
.kr-lane-context+.kr-lane-context{margin-top:5px}.kr-lane-context::after{border-color:@namContextFrame}
.kr-lane-rail{display:flex;align-items:center;justify-content:center;min-height:92px;margin:4px 0;border-right:1px solid @namLine}
.kr-lane-rail>span{writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap;padding:9px 0;color:var(--kr-tone);font-size:.7rem;font-weight:650}
.kr-lane-context>.kr-lane-rail>span{color:@namInk;font-size:.61rem;letter-spacing:.1em}
.kr-lane-body{min-width:0;padding:4px 0}.kr-board-row{position:relative;min-height:78px;background:color-mix(in srgb,var(--kr-tone) 3%,@namBg)}
.kr-lane-label{display:flex;align-items:center;min-width:0;padding:10px 8px}.kr-lane-title{display:block;border-left:2px solid var(--kr-tone);padding-left:7px;color:var(--kr-tone);font-size:.77rem;font-weight:650;overflow-wrap:anywhere}
.kr-lane-caption,.kr-activity-caption{display:block;margin-top:3px;color:@namMuted;font-size:.64rem;font-weight:400;line-height:1.4;white-space:pre-line}
.kr-board-cell{display:flex;align-items:flex-start;min-width:0;padding:10px 9px}.kr-board .kr-activity-list{display:grid;gap:5px;width:100%;list-style:none;margin:0;padding:0}
.kr-board .kr-activity{display:grid;grid-template-rows:minmax(var(--card-title-height,1.0395rem),max-content) minmax(var(--card-caption-height,1.792rem),max-content);grid-template-columns:minmax(0,1fr) 14px;gap:3px 4px;align-content:start;margin:0;padding:7px 8px;background:@namPanel;border:1px solid @namCardLine;border-radius:5px;min-width:0;overflow-wrap:anywhere}
.kr-board .kr-activity>a{grid-area:1/1;min-width:0;display:block;color:@namInk;font-size:.77rem;font-weight:650;text-decoration:none;line-height:1.35}.kr-board .kr-activity>a:hover{text-decoration:underline}
.kr-board .kr-activity>.kr-activity-caption{grid-area:2/1;min-width:0;margin:0}.kr-board .kr-activity>.kr-activity-priority{grid-area:1/2;align-self:start;justify-self:center;margin:0;height:1.0395rem}
.kr-board .kr-activity>a:focus-visible{outline:2px solid @namBrand;outline-offset:3px}
.kr-activity-priority{display:flex;align-items:center;justify-content:center}.kr-activity-priority i{display:block;width:6px;height:6px;border-radius:50%}
.kr-priority-legend{display:flex;justify-content:flex-end;gap:14px;margin:0 4px 6px;color:@namMuted;font-size:.65rem}.kr-priority-legend i{display:inline-block;width:6px;height:6px;margin-right:5px;border-radius:50%}
.kr-board-empty{font-size:.85rem;color:@namMuted;margin:14px 0 0}
""")


def render(model, activity_keys):
    """Reuse the board hierarchy and tracking for explicitly assigned activities.

    Membership never widens KR assignments. Copies are pruned so rendering
    one result never changes the shared board or another result's activities.
    """
    # board imports views for report links; loading it here avoids an import cycle.
    from . import board

    requested = set(activity_keys)
    if not requested:
        return '<p class="kr-board-empty">Noch keine Aktivitäten zugeordnet.</p>'
    original = board.lanes(model)

    def cards(lanes):
        for lane in lanes:
            for cell in lane['cells'].values():
                yield from cell
            yield from cards(lane['sublanes'])

    keys = {card['key'] for card in cards(original)}
    selected = requested & keys

    def prune(lane):
        cells = {status: [card for card in items if card['key'] in selected]
                 for status, items in lane['cells'].items()}
        sublanes = [child for source in lane['sublanes'] if (child := prune(source))]
        return dict(lane, cells=cells, sublanes=sublanes) if any(cells.values()) or sublanes else None

    lanes = [lane for original_lane in original if (lane := prune(original_lane))]
    if not lanes:
        return '<p class="kr-board-empty">Keine zugeordneten Aktivitäten im Portfolio vorhanden.</p>'
    shown_columns = board.columns(lanes)
    rail_count = max(len(row['rails']) for row in board.display_rows(lanes))
    label_width = 132 + 28 * rail_count
    out = ['<div class="kr-board" tabindex="0" role="region" aria-label="Zugeordnete Aktivitäten nach Status und Bereich; horizontal scrollbar">',
           '<div class="kr-priority-legend" aria-label="Prioritäten">' + ''.join(
               '<span><i style="background:#' + palette.HEX[color] + '" aria-hidden="true"></i>' + priority + '</span>'
               for priority, color in board.DOTS.items()) + '</div>',
           '<div class="kr-board-sheet" style="--kr-labels:' + str(label_width) + 'px;--status-count:' + str(len(shown_columns)) + '">',
           '<div class="kr-board-columns" aria-hidden="true">']
    for status, _ in shown_columns:
        out.append('<span style="--kr-status:#' + board.STATUS_COLORS[status] + '"></span>')
    out.append('</div><div class="kr-board-head"><div>Bereich / Aktivität</div>')
    for status, label in shown_columns:
        out.append('<div class="kr-board-status" style="--kr-status:#' + board.STATUS_COLORS[status] + '">' + escape(label) + '</div>')
    out.append('</div>')

    def render_row(lane, depth, label):
        out.append('<div class="kr-board-row" data-lane="' + escape(lane['key'], quote=True) +
                   '" style="--kr-tone:#' + palette.HEX[lane['tone']] +
                   ';--kr-remaining:calc(var(--kr-labels) - ' + str(28 * depth) + 'px)">')
        out.append('<div class="kr-lane-label">')
        if label:
            out.append('<span class="kr-lane-title">' + escape(lane['title']))
            if lane['caption']:
                out.append('<span class="kr-lane-caption">' + escape(lane['caption']) + '</span>')
            out.append('</span>')
        out.append('</div>')
        for status, status_label in shown_columns:
            out.append('<div class="kr-board-cell" aria-label="' + escape(status_label, quote=True) + '"><ul class="kr-activity-list">')
            for card in lane['cells'][status]:
                out.append('<li class="kr-activity" data-activity="' + escape(card['key'], quote=True) +
                           '"><a href="' + escape(activity_pdf(card), quote=True) + '">' + board.card_title(card) + '</a>')
                if card['caption']:
                    out.append('<span class="kr-activity-caption">' + escape(card['caption']) + '</span>')
                out.append(board.priority_marker(card, 'kr-activity-priority'))
                out.append(board.next_marker(card))
                out.append('</li>')
            out.append('</ul></div>')
        out.append('</div>')

    def render_lane(lane, depth=0):
        if lane['kind'] == 'lane' and not lane['sublanes']:
            render_row(lane, depth, True)
            return
        out.append('<section class="kr-lane kr-lane-' + lane['kind'] + '" data-group="' + escape(lane['key'], quote=True) +
                   '" style="--kr-tone:#' + palette.HEX[lane['tone']] + '" aria-label="' +
                   escape(lane.get('description', lane['title']), quote=True) + '">')
        out.append('<div class="kr-lane-rail"><span>' + escape(lane['title']) + '</span></div><div class="kr-lane-body">')
        if any(lane['cells'].values()):
            render_row(lane, depth + 1, False)
        for child in lane['sublanes']:
            render_lane(child, depth + 1)
        out.append('</div></section>')

    for lane in lanes:
        render_lane(lane)
    out.append('</div></div>')
    return ''.join(out)
