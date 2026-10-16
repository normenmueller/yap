-- Explicit Markdown layout without matching or rewriting the author's wording.
function Div(div)
  if FORMAT:match('latex') and div.classes:includes('synonyms') then
    div.content:insert(1, pandoc.RawBlock('latex', '\\begingroup\\small\\color{namMuted}'))
    div.content:insert(pandoc.RawBlock('latex', '\\par\\endgroup'))
    return div.content
  end
  if FORMAT:match('latex') and div.classes:includes('align-right') then
    div.content:insert(1, pandoc.RawBlock('latex', '{\\raggedleft'))
    div.content:insert(pandoc.RawBlock('latex', '\\par}'))
    return div.content
  end
end

-- Color is inherited from heading attributes; leaf sections become cards.
-- This follows the document hierarchy rather than project names or prose.
local tones = {violet = 'namViolet', orange = 'namOrange', green = 'namGreen', epistemics = 'namEpistemics', yellow = 'namStrategy', muted = 'namMuted'}

function Pandoc(doc)
  if not FORMAT:match('latex') then return nil end
  local result, stack = pandoc.List(), {}
  local chapter_pages = false
  for i, block in ipairs(doc.blocks) do
    local category_page = false
    local chapter_label = false
    if block.t == 'Header' then
      while #stack > 0 and stack[#stack].level >= block.level do
        if stack[#stack].card then
          result:insert(pandoc.RawBlock('latex', '\\end{namcard}'))
        end
        table.remove(stack)
      end
      if block.level == 1 then
        chapter_pages = block.classes:includes('chapter-pages')
        chapter_label = chapter_pages
      end
      category_page = chapter_pages and block.level == 2
      if category_page then
        result:insert(pandoc.RawBlock('latex', '\\namnextcategory'))
        result:insert(pandoc.RawBlock('latex', '\\nammagazineheading'))
      elseif block.classes:includes('new-page') then
        result:insert(pandoc.RawBlock('latex', '\\clearpage'))
      end
      local color = #stack > 0 and stack[#stack].color or 'namMuted'
      local tone = block.attributes.tone
      if tone then
        color = tones[tone]
        if not color then error('Unknown heading tone: ' .. tone .. '. Use violet, orange, green, epistemics, yellow, or muted.') end
      end
      if block.classes:includes('tone-heading') then
        block.content:insert(1, pandoc.RawInline('latex', '\\textcolor{' .. color .. '}{'))
        block.content:insert(pandoc.RawInline('latex', '}'))
      end
      stack[#stack + 1] = {level = block.level, color = color}
      local leaf = true
      for j = i + 1, #doc.blocks do
        if doc.blocks[j].t == 'Header' then
          leaf = doc.blocks[j].level <= block.level
          break
        end
      end
      if block.level >= 2 and not block.classes:includes('no-card')
          and (leaf or block.classes:includes('card')) then
        result:insert(pandoc.RawBlock('latex', '\\begin{namcard}{' .. color .. '}'))
        stack[#stack].card = true
      end
    end
    if chapter_label then
      local title = pandoc.write(pandoc.Pandoc({pandoc.Plain(block.content)}), 'latex'):gsub('%s+$', '')
      local map = block.attributes.map
      if not map or map == '' then
        error('Chapter pages require a generated map image.')
      end
      result:insert(pandoc.RawBlock('latex', '\\namchapter{' .. title .. '}{' .. block.identifier .. '}{' .. map .. '}'))
    else
      result:insert(block)
    end
    if category_page then
      result:insert(pandoc.RawBlock('latex', '\\namregularheading'))
    end
  end
  for i = #stack, 1, -1 do
    if stack[i].card then result:insert(pandoc.RawBlock('latex', '\\end{namcard}')) end
  end
  doc.blocks = result
  return doc
end
