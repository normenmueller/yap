-- Semantic heading attributes; project names are deliberately irrelevant.
local colors = {ibx = 'namBabyBlue', wip = 'namWip', ['on hold'] = 'namHold', released = 'namGreen'}
local priorities = {p1 = 'namAccent', p2 = 'namMarkerOrange', p3 = 'namBabyBlue', p4 = 'namPriorityLow'}

function Span(span)
  if FORMAT:match('latex') and span.classes:includes('personal-addition') then
    span.content:insert(1, pandoc.RawInline('latex', '\\textcolor{namPersonalAddition}{'))
    span.content:insert(pandoc.RawInline('latex', '}'))
    return span
  end
end

function Header(header)
  local status = header.attributes.status
  local priority = header.attributes.priority
  if not status and not priority then return nil end
  if status and not colors[status] then
    error('Unknown activity status: ' .. status .. '. Use ibx, wip, on hold, or released.')
  end
  if priority and not priorities[priority] then
    error('Unknown activity priority: ' .. priority .. '. Use p1, p2, p3, or p4.')
  end
  if priority then
    if FORMAT:match('latex') then
      header.content:insert(pandoc.RawInline('latex', '\\nampriority{' .. priorities[priority] .. '}{' .. priority .. '}'))
    else
      header.content:insert(pandoc.Str(' (' .. priority .. ')'))
    end
  end
  if status then
    if FORMAT:match('latex') then
      header.content:insert(pandoc.RawInline('latex', '\\namstatus{' .. colors[status] .. '}{' .. status .. '}'))
    else
      header.content:insert(pandoc.Str(' (' .. status .. ')'))
    end
  end
  return header
end
