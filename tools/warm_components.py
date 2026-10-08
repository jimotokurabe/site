"""Reusable warm, family-oriented components for generated pages."""


def family_hero(base=''):
    """Return the illustration and short message for the normal page flow."""
    return (
        '<div class="warm-scene">'
        '<p class="warm-speech">これからのお出かけ、<br>一緒に考えてみよう。</p>'
        '<div class="warm-portrait">'
        f'<img src="{base}assets/family-guide.webp" '
        'alt="親子で地域の案内を確認しているイラスト" width="1536" height="1024">'
        '</div>'
        '</div>'
    )


def family_strip(base=''):
    """Return a compact invitation to open the family conversation dialog."""
    return (
        '<section class="warm-family" aria-labelledby="warm-family-title">'
        f'<img class="warm-family-portrait" src="{base}assets/family-guide.webp" '
        'alt="親子で地域の案内を確認しているイラスト" width="1536" height="1024">'
        '<div><p class="eyebrow">家族で話す、最初のひとこと</p>'
        '<h2 id="warm-family-title">「これからのお出かけ、<br>一緒に考えてみよう。」</h2>'
        '<p>返納を決める前に、地域の特典や移動手段を一緒に。</p></div>'
        '<button type="button" data-family-open>話し始めるヒント</button>'
        '</section>'
    )


def family_dialog():
    """Return the accessible dialog used to choose and copy an opening phrase."""
    return '''<dialog id="warm-family-dialog" aria-labelledby="warm-family-dialog-title">
  <form method="dialog"><button type="submit" aria-label="閉じる">閉じる</button></form>
  <p class="eyebrow">家族で話す、最初のひとこと</p>
  <h2 id="warm-family-dialog-title">本人の気持ちを大切に、話し始めてみましょう</h2>
  <p>返納を決めるためではなく、これからの移動を一緒に考えるための言葉の例です。</p>
  <div role="group" aria-label="ひとことの例">
    <button type="button" data-family-phrase="0" aria-pressed="true">気持ちを聞く</button>
    <button type="button" data-family-phrase="1" aria-pressed="false">移動を考える</button>
    <button type="button" data-family-phrase="2" aria-pressed="false">一緒に調べる</button>
  </div>
  <blockquote data-family-phrase-output>これからのお出かけ、一緒に考えてみよう。</blockquote>
  <p role="status" aria-live="polite" data-family-copy-status></p>
  <button type="button" data-family-copy>このひと言をコピー</button>
  <button type="button" data-family-close>閉じる</button>
</dialog>'''
