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


def family_dialog(base=''):
    """Choose a situation, an opening and an optional response without a quiz."""
    return f'''<dialog id="warm-family-dialog" aria-labelledby="warm-family-dialog-title">
  <form method="dialog" class="family-close-row"><button type="submit" aria-label="閉じる">閉じる ×</button></form>
  <p class="family-eyebrow">家族で話す、小さなきっかけ</p>
  <h2 id="warm-family-dialog-title">話し始めるヒント</h2>
  <p class="family-intro">場面を選ぶと、ひと言と会話の続け方が見つかります。</p>
  <div class="family-scenes" role="group" aria-label="話す場面">
    <button type="button" data-family-phrase="0" aria-pressed="true">まず気持ちを聞く</button>
    <button type="button" data-family-phrase="1" aria-pressed="false">通院・買い物</button>
    <button type="button" data-family-phrase="2" aria-pressed="false">免許の更新</button>
    <button type="button" data-family-phrase="3" aria-pressed="false">ヒヤッとしたとき</button>
    <button type="button" data-family-phrase="4" aria-pressed="false">お金の話</button>
    <button type="button" data-family-phrase="5" aria-pressed="false">離れて暮らす家族</button>
  </div>
  <section class="family-opening" aria-labelledby="family-opening-title">
    <h3 id="family-opening-title">こんなふうに、話し始める</h3>
    <blockquote data-family-phrase-output aria-live="polite">これからのお出かけ、一緒に考えてみよう。最近、運転していて気になることはある？</blockquote>
    <div class="family-actions"><button type="button" data-family-another>別の言い方を見る</button><span data-family-count>1 / 3</span><button type="button" data-family-copy>ひと言をコピー</button></div>
  </section>
  <details class="family-reaction"><summary>こんな返事が返ってきたら？</summary>
    <p>近い返事を選んでみてください。</p>
    <div role="group" aria-label="相手の返事">
      <button type="button" data-family-reaction="0" aria-pressed="false">まだ大丈夫</button>
      <button type="button" data-family-reaction="1" aria-pressed="false">車がないと困る</button>
      <button type="button" data-family-reaction="2" aria-pressed="false">今は話したくない</button>
    </div>
    <div class="family-reply" data-family-reply hidden><h3>こんな返し方も</h3><p data-family-reply-output aria-live="polite"></p></div>
  </details>
  <div class="family-next"><h3>次に一緒にできること</h3><p data-family-next>これからも続けたいお出かけを、一つ聞いてみる。</p><a href="{base}outing-plan.html">車なしのお出かけ計画を作る →</a></div>
  <details class="family-tips"><summary>話す前に、ひとつだけ</summary><ul>
    <li>「危ないから返して」より、「私はあの場面が心配だった」と具体的に。</li>
    <li>本人の話を聞く時間を。今日、結論が出なくても大丈夫。</li>
    <li>できる範囲を伝えて、送迎などの約束を決めつけない。</li>
  </ul></details>
  <div class="family-actions family-save"><button type="button" data-family-memo>選んだ会話をメモにコピー</button></div>
  <p role="status" aria-live="polite" data-family-copy-status></p>
  <p class="family-credit">じもとくらべが作成した会話の例です。本人の意思を尊重し、運転中は話し合いを避けましょう。</p>
  <a class="family-more-link" href="{base}henno-hanashikata.html">6つの質問で、自分たちに合うひと言を探す →</a>
</dialog>'''
