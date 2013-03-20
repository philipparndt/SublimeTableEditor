# table_plugin.py - sublime plugins for pretty print text table

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

import sublime
import sublime_plugin
import csv
import re
import tablelib

class TableContext:

    def __init__(self, view, sel, syntax):
        self.view = view
        (self.sel_row, self.sel_col) = self.view.rowcol(sel.begin())
        self.syntax = syntax
        self.field_num = self._get_unformatted_field_num()
        self.first_table_row = self._get_first_table_row()
        self.last_table_row = self._get_last_table_row()
        self.table_text = self._get_table_text()

    def _get_table_text(self):
        begin_point = self.view.line(
                                     self.view.text_point(self.first_table_row, 0)
                                    ).begin()
        end_point = self.view.line(
                                   self.view.text_point(self.last_table_row, 0)
                                   ).end()
        return self.view.substr(sublime.Region(begin_point, end_point))

    def _get_last_table_row(self):
        row = self.sel_row
        last_table_row = self.sel_row
        last_line = self._get_last_buffer_row()
        while (row <= last_line and self._is_table_row(row)):
            last_table_row = row
            row = row + 1
        return last_table_row

    def _get_first_table_row(self):
        row = self.sel_row
        first_table_row = self.sel_row
        while (row >= 0 and self._is_table_row(row)):
            first_table_row = row
            row = row - 1
        return first_table_row

    def _is_table_row(self, row):
        return re.match(r"^\s*" + self.syntax.hline_border_pattern(),
                        self._get_text(row)) is not None

    def _get_unformatted_field_num(self):
        line_text = self._get_text(self.sel_row)
        sel_field_num = self._hline_count(line_text, 0, self.sel_col) - 1
        mo = re.compile(r"\s*$")
        if sel_field_num > 0 and mo.match(line_text, self.sel_col):
            sel_field_num = sel_field_num - 1
        return sel_field_num

    #not used
    def _get_field_num(self, row, col):
        return self.hline_count(self.get_text(row), 0, col) - 1

    def _hline_count(self, text, start, end):
        if self.syntax.is_hline(text):
            return sum([text.count(ch, start, end)
                                        for ch in self.syntax.hline_borders])
        else:
            return text.count(self.syntax.vline, start, end)

    def _get_text(self, row):
        point = self.view.text_point(row, 0)
        region = self.view.line(point)
        text = self.view.substr(region)
        return text

    def _get_last_buffer_row(self):
        return self.view.rowcol(self.view.size())[0]


class AbstractTableCommand(sublime_plugin.TextCommand):

    @property
    def syntax(self):
        syntax_name = self.view.settings().get("table_editor_syntax")
        if syntax_name == "Simple":
            syntax = tablelib.simple_syntax()
        elif syntax_name == "EmacsOrgMode":
            syntax = tablelib.emacs_org_mode_syntax()
        elif syntax_name == "Pandoc":
            syntax = tablelib.pandoc_syntax()
        elif syntax_name == "MultiMarkdown":
            syntax = tablelib.multi_markdown_syntax()
        elif syntax_name == "reStructuredText":
            syntax = tablelib.re_structured_text_syntax()
        elif syntax_name == "Textile":
            syntax = tablelib.textile_syntax()
        else:
            syntax = self.auto_detect_syntax()
        border_style = (self.view.settings().get("table_editor_border_style",
                                                   None) or
                         self.view.settings().get("table_editor_style",
                         None))
        if border_style == "emacs":
            syntax.hline_out_border = '|'
            syntax.hline_in_border = '+'
        elif border_style == "grid":
            syntax.hline_out_border = '+'
            syntax.hline_in_border = '+'
        elif border_style == "simple":
            syntax.hline_out_border = '|'
            syntax.hline_in_border = '|'

        if self.view.settings().has("table_editor_custom_column_alignment"):
            syntax.custom_column_alignment = self.view.settings().get("table_editor_custom_column_alignment")

        if self.view.settings().has("table_editor_keep_space_left"):
            syntax.keep_space_left = self.view.settings().get("table_editor_keep_space_left")

        if self.view.settings().has("table_editor_align_number_right"):
            syntax.align_number_right = self.view.settings().get("table_editor_align_number_right")

        if self.view.settings().has("table_editor_detect_header"):
            syntax.detect_header = self.view.settings().get("table_editor_detect_header")

        return syntax


    def auto_detect_syntax(self):
        view_syntax = self.view.settings().get('syntax')
        if (view_syntax == 'Packages/Markdown/MultiMarkdown.tmLanguage' or
            view_syntax == 'Packages/Markdown/Markdown.tmLanguage'):
            return tablelib.multi_markdown_syntax()
        elif view_syntax == 'Packages/Textile/Textile.tmLanguage':
            return tablelib.textile_syntax()
        elif (view_syntax ==
                     'Packages/RestructuredText/reStructuredText.tmLanguage'):
            return tablelib.re_structured_text_syntax()
        else:
            return tablelib.simple_syntax()
        #'Packages/Text/Plain text.tmLanguage':
        #

    def csv2table(self, text):
        lines = []
        try:
            vline = self.syntax.vline
            dialect = csv.Sniffer().sniff(text)
            table_reader = csv.reader(text.splitlines(), dialect)
            for row in table_reader:
                lines.append(vline + vline.join(row) + vline)
        except csv.Error:
            for row in text.splitlines():
                lines.append(vline + row + vline)
        return "\n".join(lines)

    def find_border(self, text, num):
        if self.syntax.is_hline(text):
            pattern = self.syntax.hline_border_pattern()
        else:
            pattern = self.syntax.vline_pattern()
        it = re.finditer(pattern, text)
        index = -1
        for i in range(num):
            try:
                mo = it.next()
                index = mo.start()
            except StopIteration:
                index = -1
        return index

    def hline_count(self, text, start, end):
        if self.syntax.is_hline(text):
            return sum([text.count(ch, start, end)
                                        for ch in self.syntax.hline_borders])
        else:
            return text.count(self.syntax.vline, start, end)

    def get_text(self, row):
        point = self.view.text_point(row, 0)
        region = self.view.line(point)
        text = self.view.substr(region)
        return text

    def get_row(self, point):
        return self.view.rowcol(point)[0]

    def is_table_row(self, row):
        return re.match(r"^\s*" + self.syntax.hline_border_pattern(),
                        self.get_text(row)) is not None



    def get_field_default_point(self, row, field_num):
        text = self.get_text(row)
        i1 = self.find_border(text, field_num + 1)
        i2 = self.find_border(text, field_num + 2)
        match = re.compile(r"([^\s])\s*$").search(text, i1 + 1, i2)
        if match:
            return self.view.text_point(row, match.start(1) + 1)
        else:
            return self.view.text_point(row, i1 + 2)





class AbstractTableMultiSelect(AbstractTableCommand):


    def merge(self, edit, ctx, table):
        new_lines = table.render_lines()
        first_table_row = ctx.first_table_row
        last_table_row = ctx.last_table_row
        rows = range(first_table_row, last_table_row + 1)
        for row, new_text in zip(rows, new_lines):
            region = self.view.line(self.view.text_point(row, 0))
            old_text = self.view.substr(region)
            if old_text != new_text:
                self.view.replace(edit, region, new_text)

        #case 1: some lines inserted
        if len(rows) < len(new_lines):
            print "case 1: some lines inserted"
            row = last_table_row
            for new_text in new_lines[len(rows):]:
                end_point = self.view.line(self.view.text_point(row, 0)).end()
                self.view.insert(edit, end_point, "\n" + new_text)
                row = row + 1
        #case 2: some lines deleted
        elif len(rows) > len(new_lines):
            print "case 2: some lines deleted"
            for row in rows[len(new_lines):]:
                region = self.view.line(self.view.text_point(row, 0))
                self.view.erase(edit, region)

    def create_table(self, ctx):
        return tablelib.TextTable(ctx.table_text, ctx.syntax)

    def run(self, edit):
        new_sels = []
        for sel in self.view.sel():
            if not self.is_table_row(self.get_row(sel.begin())):
                new_sels.append(sel)
                continue
            new_sel = self.run_one_sel(edit, sel)
            new_sels.append(new_sel)
        self.view.sel().clear()
        for sel in new_sels:
            self.view.sel().add(sel)
            self.view.show(sel, False)

    def run_one_sel(self, edit, sel):
        return sel


class TableEditorAlignCommand(AbstractTableMultiSelect):
    """
    Key: ctrl+shift+a
    Re-align the table without change the current table field.
    Move cursor to begin of the current table field.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(ctx.sel_row, ctx.field_num)
        return sublime.Region(pt, pt)


class TableEditorNextField(AbstractTableMultiSelect):
    """
    Key: tab
    Re-align the table, move to the next field.
    Creates a new row if necessary.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)
        self.merge(edit, ctx, table)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        moved = False
        while True:
            if table[sel_row - ctx.first_table_row].is_separator():
                if sel_row < ctx.last_table_row:
                    sel_row = sel_row + 1
                    field_num = 0
                    moved = True
                    continue
                else:
                    #sel_row == last_table_row
                    table.insert_empty_row(table.row_count)
                    self.merge(edit, ctx, table)
                    field_num = 0
                    sel_row += 1
                    break
            elif moved:
                break
            elif field_num + 1 < table.column_count:
                field_num = field_num + 1
                break
            elif sel_row < ctx.last_table_row:
                field_num = 0
                sel_row = sel_row + 1
                moved = True
                continue
            else:
                #sel_row == last_table_row
                table.insert_empty_row(table.row_count)
                self.merge(edit, ctx, table)
                field_num = 0
                sel_row += 1
                break
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorPreviousField(AbstractTableMultiSelect):
    """
    Key: shift+tab
    Re-align, move to previous field.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)
        self.merge(edit, ctx, table)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        moved = False
        while True:
            if table[sel_row - ctx.first_table_row].is_separator():
                if sel_row > ctx.first_table_row:
                    sel_row = sel_row - 1
                    field_num = table.column_count - 1
                    moved = True
                    continue
                else:
                    #sel_row == first_table_row:
                    field_num = 0
                    break
            elif moved:
                break
            elif field_num > 0:
                field_num = field_num - 1
                break
            elif sel_row > ctx.first_table_row:
                sel_row = sel_row - 1
                field_num = table.column_count - 1
                moved = True
                continue
            else:
                #sel_row == first_table_row:
                break
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorNextRow(AbstractTableMultiSelect):
    """
    Key: enter
    Re-align the table and move down to next row.
    Creates a new row if necessary.
    At the beginning or end of a line, enter still does new line.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)
        self.merge(edit, ctx, table)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        if sel_row < ctx.last_table_row:
            if table[sel_row - ctx.first_table_row + 1].is_separator():
                table.insert_empty_row(sel_row - ctx.first_table_row + 1)
                self.merge(edit, ctx, table)
        else:
            table.insert_empty_row(table.row_count)
            self.merge(edit, ctx, table)
        sel_row += 1
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorMoveColumnLeft(AbstractTableMultiSelect):
    """
    Key: alt+left
    Move the current column right.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        if field_num > 0:
            table.swap_columns(field_num, field_num - 1)
            field_num = field_num - 1
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorMoveColumnRight(AbstractTableMultiSelect):
    """
    Key: alt+right
    Move the current column right.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        if field_num < table.column_count - 1:
            table.swap_columns(field_num, field_num + 1)
            field_num = field_num + 1
        self.merge(edit,ctx.first_table_row, ctx.last_table_row, table.render_lines())
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorDeleteColumn(AbstractTableMultiSelect):
    """
    Key: alt+shift+left
    Kill the current column.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        table.delete_column(field_num)
        self.merge(edit, ctx, table)
        if table.column_count == 0:
            pt = self.view.text_point(ctx.first_table_row, 0)
        else:
            if field_num == table.column_count:
                field_num = field_num - 1
            pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)




class TableEditorInsertColumn(AbstractTableMultiSelect):
    """
    Keys: alt+shift+right
    Insert a new column to the left of the cursor position.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        table.insert_empty_column(field_num)
        self.merge(edit,ctx.first_table_row, ctx.last_table_row, table.render_lines())
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorKillRow(AbstractTableMultiSelect):
    """
    Key : alt+shift+up
    Kill the current row or horizontal line.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        table.delete_row(sel_row - ctx.first_table_row)
        self.merge(edit,ctx.first_table_row, ctx.last_table_row, table.render_lines())
        if ctx.first_table_row == ctx.last_table_row:
            pt = self.view.text_point(sel_row, 0)
        else:
            if sel_row == ctx.last_table_row:
                sel_row = sel_row - 1
            pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)



class TableEditorInsertRow(AbstractTableMultiSelect):
    """
    Key: alt+shift+down
    Insert a new row above the current row.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        table.insert_empty_row(sel_row - ctx.first_table_row)
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorMoveRowUp(AbstractTableMultiSelect):
    """
    Key: alt+up
    Move the current row up.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        row_num = sel_row - ctx.first_table_row
        if sel_row > ctx.first_table_row:
            table.swap_rows(row_num, row_num - 1)
            sel_row = sel_row - 1
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)



class TableEditorMoveRowDown(AbstractTableMultiSelect):
    """
    Key: alt+down
    Move the current row down.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        row_num = sel_row - ctx.first_table_row
        if sel_row < ctx.last_table_row:
            table.swap_rows(row_num, row_num + 1)
            sel_row = sel_row + 1
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorInsertSingleHline(AbstractTableMultiSelect):
    """
    Key: ctrl+k,-
    Insert single horizontal line below current row.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        row_num = sel_row - ctx.first_table_row
        table.insert_single_separator_row(row_num + 1)
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)

class TableEditorInsertDoubleHline(AbstractTableMultiSelect):
    """
    Key: ctrl+k,=
    Insert double horizontal line below current row.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        row_num = sel_row - ctx.first_table_row
        table.insert_double_separator_row(row_num + 1)
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorHlineAndMove(AbstractTableMultiSelect):
    """
    Key: ctrl+k, enter
    Insert a horizontal line below current row,
    and move the cursor into the row below that line.
    """

    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        self.merge(edit, ctx, table)

        row_num = sel_row - ctx.first_table_row
        table.insert_single_separator_row(row_num + 1)

        if row_num + 2 < table.row_count:
            if table[row_num + 2].is_separator():
                table.insert_empty_row(row_num + 2)
        else:
            table.insert_empty_row(row_num + 2)
        self.merge(edit, ctx, table)

        sel_row = sel_row + 2
        pt = self.get_field_default_point(sel_row, 0)
        return sublime.Region(pt, pt)


class TableEditorSplitColumnDown(AbstractTableMultiSelect):
    """
    Key: alt+enter
    Split rest of cell down from current cursor position,
    insert new line bellow if current row is last row in the table
    or if next line is hline
    """
    def remove_rest_line(self, edit, sel):
        end_region = self.view.find(self.syntax.hline_border_pattern(),
                                    sel.begin())
        rest_region = sublime.Region(sel.begin(), end_region.begin())
        rest_data = self.view.substr(rest_region)
        self.view.replace(edit, rest_region, "")
        return rest_data.strip()

    def run_one_sel(self, edit, sel):
        (sel_row, sel_col) = self.view.rowcol(sel.begin())
        rest_data = self.remove_rest_line(edit, sel)

        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        if sel_row == ctx.last_table_row or table[sel_row - ctx.first_table_row + 1].is_separator():
            table.insert_empty_row(sel_row - ctx.first_table_row + 1)
        sel_row = sel_row + 1
        row_num = sel_row - ctx.first_table_row
        table[row_num][field_num].data = rest_data + " " + table[row_num][field_num].data.strip()
        table.pack()
        self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)



class TableEditorJoinLines(AbstractTableMultiSelect):
    """
    Key: ctrl+j
    Join current row and next row into one if next row is not hline
    """
    def run_one_sel(self, edit, sel):
        ctx = TableContext(self.view, sel, self.syntax)
        table = self.create_table(ctx)

        sel_row = ctx.sel_row
        field_num = ctx.field_num

        self.merge(edit, ctx, table)

        row_num = sel_row - ctx.first_table_row
        if (row_num < table.row_count
            and table[row_num].is_data()
            and table[row_num + 1].is_data()):
            for curr_col, next_col in zip(table[row_num].columns,
                                          table[row_num +1].columns):
                curr_col.data = curr_col.data.strip() + " " + next_col.data.strip()

            table.delete_row(row_num + 1)
            self.merge(edit, ctx, table)
        pt = self.get_field_default_point(sel_row, field_num)
        return sublime.Region(pt, pt)


class TableEditorCsvToTable(AbstractTableCommand):
    """
    Command: table_csv_to_table
    Key: ctrl+k, |
    Convert selected CSV region into table
    """
    def run(self, edit):
        new_sels = []
        for sel in self.view.sel():
            (sel_row, sel_col) = self.view.rowcol(sel.begin())
            if sel.empty():
                new_sels.append(sel)
            else:
                text = self.view.substr(sel)
                new_text = self.csv2table(text)
                self.view.replace(edit, sel, new_text)
                pt = self.get_field_default_point(sel_row, 0)
                new_sels.append(sublime.Region(pt, pt))
        self.view.sel().clear()
        for sel in new_sels:
            self.view.sel().add(sel)
            self.view.show(sel, False)
        self.view.run_command("table_editor_align")


class TableEditorDisableForCurrentView(sublime_plugin.TextCommand):

    def run(self, args, prop):
        self.view.settings().set(prop, False)


class TableEditorEnableForCurrentView(sublime_plugin.TextCommand):

    def run(self, args, prop):
        self.view.settings().set(prop, True)


class TableEditorDisableForCurrentSyntax(sublime_plugin.TextCommand):

    def run(self, edit):
        syntax = self.view.settings().get('syntax')
        if syntax is not None:
            m = re.search("([^/]+)[.]tmLanguage$", syntax)
            if m:
                base_name = m.group(1) + ".sublime-settings"
                settings = sublime.load_settings(base_name)
                settings.erase("enable_table_editor")
                sublime.save_settings(base_name)


class TableEditorEnableForCurrentSyntax(sublime_plugin.TextCommand):

    def run(self, edit):
        syntax = self.view.settings().get('syntax')
        if syntax is not None:
            m = re.search("([^/]+)[.]tmLanguage$", syntax)
            if m:
                base_name = m.group(1) + ".sublime-settings"
                settings = sublime.load_settings(base_name)
                settings.set("enable_table_editor", True)
                sublime.save_settings(base_name)


class TableEditorSetSyntax(sublime_plugin.TextCommand):

    def run(self, edit, syntax):
        self.view.settings().set("enable_table_editor", True)
        self.view.settings().set("table_editor_syntax", syntax)
        sublime.status_message("Table Editor: set syntax to '{0}'"
                               .format(syntax))
