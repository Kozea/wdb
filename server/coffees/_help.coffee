help = """
<div class="mdl-tabs mdl-js-tabs mdl-js-ripple-effect">
  <div class="mdl-tabs__tab-bar">
      <a href="#help-stepping" class="mdl-tabs__tab is-active">Stepping</a>
      <a href="#help-breakpoints" class="mdl-tabs__tab">Breakpoints</a>
      <a href="#help-inspecting" class="mdl-tabs__tab">Inspecting</a>
      <a href="#help-prompt" class="mdl-tabs__tab">Prompt</a>
      <a href="#help-misc" class="mdl-tabs__tab">Misc</a>
  </div>

  <div class="mdl-tabs__panel is-active" id="help-stepping">
    <table class="mdl-data-table mdl-js-data-table mdl-shadow--2dp">
      <tr>
        <td class="cmd">
          <samp>.s</samp> or <kbd>Alt</kbd> + <kbd>↓</kbd> or <kbd>F11</kbd>
        </td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Step into
        </td>
      </tr>
      <tr>
        <td class="cmd">
          <samp>.n</samp> or <kbd>Alt</kbd> + <kbd>→</kbd> or <kbd>F10</kbd>
        </td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Step over (Next)
        </td>
      </tr>
      <tr>
        <td class="cmd">
          <samp>.u</samp> or <kbd>Alt</kbd> + <kbd>←</kbd> or <kbd>F7</kbd>
        </td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Until (Next over loops)
        </td>
      </tr>
      <tr>
        <td class="cmd">
          <samp>.r</samp> or <kbd>Alt</kbd> + <kbd>↑</kbd> or <kbd>F9</kbd>
        </td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Step out (Return)
        </td>
      </tr>
      <tr>
        <td class="cmd">
          <samp>.c</samp> or <kbd>Alt</kbd> + <kbd>Enter</kbd> or <kbd>F8</kbd>
        </td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Continue
        </td>
      </tr>
      <tr>
        <td class="cmd"><samp>.j</samp> lineno</td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Jump to lineno (Must be at bottom frame and in the same function)
        </td>
      </tr>
      <tr>
        <td class="cmd"><samp>.q</samp></td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Quit
        </td>
      </tr>
    </table>
    <aside class="note">
      All commands are prefixed with a dot and can be
      executed with <kbd>Alt</kbd> + <kbd>the-command-letter</kbd>,
      i.e.: <kbd>Alt</kbd> + <kbd>h</kbd>
    </aside>
  </div>
  <div class="mdl-tabs__panel" id="help-breakpoints">
    <table class="mdl-data-table mdl-js-data-table mdl-shadow--2dp">
      <tr>
        <td class="cmd"><samp>.b</samp> arg</td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Set a session breakpoint
        </td>
      </tr>
      <tr>
        <td class="cmd"><samp>.t</samp> arg</td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Set a temporary breakpoint
        </td>
      </tr>
      <tr>
        <td class="cmd"><samp>.z</samp> arg</td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Delete existing breakpoint
        </td>
      </tr>
      <tr>
        <td class="cmd"><samp>.l</samp></td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          List active breakpoints
        </td>
      </tr>
      <tr>
        <td class="cmd">Breakpoint argument format</td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          <code>[file/module][:lineno][#function][,condition]</code>
        </td>
      </tr>
      <tr>
        <td class="cmd"><code>[file]</code></td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Break if any line of <code>file</code> is executed</td>
      </tr>
      <tr>
        <td class="cmd"><code>[file]:lineno</code></td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Break on <code>file</code> at <code>lineno</code></td>
      </tr>
      <tr>
        <td class="cmd"><code>[file][:lineno],condition</code></td>
        <td class="mdl-data-table__cell--non-numeric dfn">
            Break on <code>file</code> at <code>lineno</code> if
            <code>condition</code> is <code>True</code>
            (ie: <code>i == 10)</code></td>
      </tr>
      <tr>
        <td class="cmd"><code>[file]#function</code></td>
        <td class="mdl-data-table__cell--non-numeric dfn">
          Break when inside <code>function</code> function</td>
      </tr>
    </table>
    <aside class="note">
      File is always current file by default and you can also
      specify a module like <code>logging.config</code>.
    </aside>
  </div>
  <div class="mdl-tabs__panel" id="help-inspecting">
    <table class="mdl-data-table mdl-js-data-table mdl-shadow--2dp">
    <tr>
      <td class="cmd"><samp>.a</samp></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Echo all typed commands in the current debugging session
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.d</samp> expression</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Dump the result of expression in a table
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.w</samp> expression</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Watch expression in current file (Click on the name to remove)
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.i</samp> [mime/type;]expression</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Display the result in an embed, mime type defaults to "text/html"
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.x</samp> left ? right</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Display the difference between the pretty print of 'left' and 'right'
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.x</samp> left <> right</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Display the difference between the repr of 'left' and 'right'
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.f</samp> key in expression</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Search recursively the presence of key in expression object tree
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.f</samp> test of expression</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Search recursively values that match test in expression inner tree.
        i.e.: .f type(x) == int of sys
      </td>
    </tr>
  </table>
</div>
<div class="mdl-tabs__panel" id="help-prompt">
  <table class="mdl-data-table mdl-js-data-table mdl-shadow--2dp">
    <tr>
      <td class="cmd">iterable!sthg</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        If <a href="https://github.com/paradoxxxzero/cutter">
          cutter
        </a> is installed, executes cut(iterable).sthg
      </td>
    </tr>
    <tr>
      <td class="cmd">expr >! file</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Write the result of expr in file
      </td>
    </tr>
    <tr>
      <td class="cmd">!< file</td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Eval the content of file
      </td>
    </tr>
    <tr>
      <td class="cmd"><kbd>Enter</kbd></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Eval the current selected text in page,
        useful to eval code in the source
      </td>
    </tr>
    <tr>
      <td class="cmd"><kbd>Shift</kbd> + <kbd>Enter</kbd></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Insert the current selected text in page in the prompt
      </td>
    </tr>
    <tr>
      <td class="cmd"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Force multiline prompt
      </td>
    </tr>
  </table>
</div>
<div class="mdl-tabs__panel" id="help-misc">
  <table class="mdl-data-table mdl-js-data-table mdl-shadow--2dp">
    <tr>
      <td class="cmd"><samp>.h</samp></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Get some help
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.m</samp></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Restart program
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.e</samp></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Toggle file edition mode
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.o</samp></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Try to open file in external ($EDITOR / $VISUAL / xdg-open) editor.
        <br>
        Add an argument (or hold shift with alt+o) if your editor does not
        support the file:lno:col syntax.
      </td>
    </tr>
    <tr>
      <td class="cmd"><samp>.g</samp></td>
      <td class="mdl-data-table__cell--non-numeric dfn">
        Clear scrollback
      </td>
    </tr>
  </table>
</div>
"""
