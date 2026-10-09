(() => {
  'use strict';

  const conversations = [
    {
      label: 'まず気持ちを聞く',
      openings: ['これからのお出かけ、一緒に考えてみよう。最近、運転していて気になることはある？', '運転で好きなことと、少し疲れること、どちらも聞いてみたいな。', '今日は何かを決めたいわけじゃないんだ。これからも大切にしたいお出かけを教えて。'],
      replies: ['そう思っているんだね。今のうちに、どんなときに運転を休みたいか聞いてもいい？', '出かけられなくなるのは困るよね。続けたい用事を一つずつ教えてくれる？', '分かった。今日はここまでにしよう。また話せそうなときに聞かせてね。'],
      next: 'これからも続けたいお出かけを、一つ聞いてみる。'
    },
    {
      label: '通院・買い物',
      openings: ['いつもの病院やお店、車以外ならどう行けるか一緒に調べてみない？', '次の買い物、試しにバスかタクシーで一緒に行ってみない？帰りも含めて考えよう。', '車が使えない日があったら、どの用事が一番困りそう？そこから一緒に考えたいな。'],
      replies: ['今は運転できていても、車を使わない日の行き方が一つあると助かるかも。一緒に試してみない？', 'そうだよね。まずは病院かお店を一つ選んで、行きと帰りの方法を調べてみよう。', '今日は調べなくても大丈夫。行き先だけ、今度よかったら教えてね。'],
      next: 'よく行く場所を一つ決め、行き・帰りの便と費用を確認する。'
    },
    {
      label: '免許の更新',
      openings: ['もうすぐ免許の更新だね。これからの運転、どんなふうに考えている？', '次の更新に向けて、運転で気になっていることや、続けたい外出を一緒に整理してみない？', '更新するかどうかを今決めるんじゃなくて、選べる方法を一緒に知っておきたいな。'],
      replies: ['今の気持ちを聞かせてくれてありがとう。これからどんな変化があったら相談したいか、考えてみない？', '移動のことが先だよね。返納の話だけでなく、今使える交通の支援も調べてみよう。', '分かった。今日は結論を出さずに、また都合のよいときに話そう。'],
      next: '本人が気になっていることを一つ整理し、必要なら公式の案内を一緒に読む。'
    },
    {
      label: 'ヒヤッとしたとき',
      openings: ['この前の運転で、私は少し心配になったんだ。そのとき、どう感じていた？', 'さっきのこと、責めたいんじゃなくて気になっているんだ。落ち着いたら話を聞いてもいい？', '気になった場面があったから、これからどうしたら安心して出かけられるか、一緒に考えたいな。'],
      replies: ['そう感じたんだね。私はあの場面が心配だったから、お互いにどう見えたか聞き合ってみない？', '出かけることは大事だよね。運転の心配と、行きたい場所への移動を、分けて考えてみよう。', '分かった。今は言い合いにしたくないから、落ち着いてから話そう。'],
      next: '落ち着ける場所で、気になった場面と本人の受け止めを一つずつ確認する。'
    },
    {
      label: 'お金の話',
      openings: ['車のお金と、バスやタクシーを使うお金、どれくらい違うか一緒に見てみない？', 'いつものお出かけを続けるには、何にどれくらいかかるんだろう。まずは一回分から調べてみようか。', '安さだけじゃなく、楽に出かけられることも大事だよね。費用と使いやすさを一緒に比べてみたいな。'],
      replies: ['今すぐ変える話ではなくて、選べる方法を知るために、実際の費用を見てみようか。', '必要な用事に無理なく行けることが先だよね。回数と行き先を決めてから比べてみよう。', '今日は数字を出さなくても大丈夫。気が向いたときに一緒に見てみよう。'],
      next: 'いつもの外出一回分について、実際の運賃や利用条件を調べる。'
    },
    {
      label: '離れて暮らす家族',
      openings: ['最近、お出かけはどうしている？遠くにいるから、いつもの様子を聞いておきたくて。', '次に帰ったとき、いつもの買い物に一緒に行ってもいい？普段の行き方を教えてほしいな。', '私がすぐ行けない日もあるから、近くで使える移動の方法を一緒に探しておきたいな。'],
      replies: ['元気に出かけられていると聞けてうれしいよ。困った日にはどう連絡するか、決めておかない？', 'すぐ送迎できない日もあるから、近くの交通や頼れる人を、本人の希望を聞きながら考えたいな。', '分かった。今日は普段の話をしよう。また話したくなったら教えてね。'],
      next: '本人の希望を聞いて、次に連絡する日か、一緒に出かける機会を決める。'
    }
  ];
  const reactions = ['まだ大丈夫', '車がないと困る', '今は話したくない'];

  function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(value).then(() => true).catch(() => legacyCopy(value));
    }
    return Promise.resolve(legacyCopy(value));
  }

  function legacyCopy(value) {
    const field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    const active = document.activeElement;
    (document.querySelector('dialog[open]') || document.body).append(field);
    field.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch (error) { copied = false; }
    field.remove();
    active?.focus({preventScroll: true});
    return copied;
  }

  const familyDialog = document.getElementById('warm-family-dialog');
  if (familyDialog) {
    const output = familyDialog.querySelector('[data-family-phrase-output]');
    const status = familyDialog.querySelector('[data-family-copy-status]');
    let scene = 0, variant = 0, reaction = null, opener = null;
    const buttons = [...familyDialog.querySelectorAll('[data-family-phrase]')];
    const replyButtons = [...familyDialog.querySelectorAll('[data-family-reaction]')];
    const reply = familyDialog.querySelector('[data-family-reply]');
    function render() {
      const item = conversations[scene];
      output.textContent = item.openings[variant];
      familyDialog.querySelector('[data-family-count]').textContent = `${variant + 1} / ${item.openings.length}`;
      familyDialog.querySelector('[data-family-next]').textContent = reaction === 2 ? '今日は話を区切り、本人が話したくなったときに改めて聞く。' : item.next;
      buttons.forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.familyPhrase) === scene)));
      replyButtons.forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.familyReaction) === reaction)));
      reply.hidden = reaction === null;
      familyDialog.querySelector('[data-family-reply-output]').textContent = reaction === null ? '' : item.replies[reaction];
      status.textContent = '';
    }
    document.querySelectorAll('[data-family-open]').forEach(button => button.addEventListener('click', () => {
      opener = button;
      status.textContent = '';
      if (typeof familyDialog.showModal === 'function') familyDialog.showModal();
      else familyDialog.setAttribute('open', '');
    }));
    familyDialog.addEventListener('close', () => opener?.focus({preventScroll: true}));
    buttons.forEach(button => button.addEventListener('click', () => {
      scene = Number(button.dataset.familyPhrase);
      if (!conversations[scene]) scene = 0;
      variant = 0; reaction = null;
      familyDialog.querySelector('.family-reaction').open = false;
      render();
    }));
    familyDialog.querySelector('[data-family-another]').addEventListener('click', () => {
      variant = (variant + 1) % conversations[scene].openings.length;
      render();
    });
    replyButtons.forEach(button => button.addEventListener('click', () => {
      reaction = Number(button.dataset.familyReaction);
      render();
    }));
    async function copyConversation(memo) {
      const item = conversations[scene];
      const text = memo
        ? `話し始めるヒント：${item.label}\n\n最初のひと言\n${item.openings[variant]}` +
          (reaction === null ? '' : `\n\n「${reactions[reaction]}」と返ってきたら\n${item.replies[reaction]}`) +
          `\n\n次に一緒にできること\n${familyDialog.querySelector('[data-family-next]').textContent}\n\nじもとくらべが作成した会話の例です。`
        : item.openings[variant];
      const copied = await copyText(text);
      status.textContent = copied ? (memo ? '選んだ会話をコピーしました。メモやメッセージに貼り付けられます。' : 'ひと言をコピーしました。') : 'コピーできませんでした。文章を選択してコピーしてください。';
    }
    familyDialog.querySelector('[data-family-copy]').addEventListener('click', () => copyConversation(false));
    familyDialog.querySelector('[data-family-memo]').addEventListener('click', () => copyConversation(true));
    render();
  }

  const checklist = [...document.querySelectorAll('#family .checklist input[type="checkbox"]')];
  const checkStatus = document.getElementById('check-status');
  if (checklist.length && checkStatus) {
    const pageKey = `jimoto-family-checks:${document.querySelector('link[rel="canonical"]')?.href || location.pathname}`;
    let storageAvailable = true;
    try {
      const saved = JSON.parse(localStorage.getItem(pageKey) || '[]');
      checklist.forEach((box, index) => { box.checked = saved[index] === true; });
    } catch (error) { storageAvailable = false; }

    const updateStatus = () => {
      const checked = checklist.filter(box => box.checked).length;
      checkStatus.textContent = `${checklist.length}項目のうち${checked}項目を確認。チェックはこの${storageAvailable ? '端末に保存されます' : 'ページを開いている間だけ保持されます'}。`;
    };
    updateStatus();
    checklist.forEach(box => box.addEventListener('change', () => {
      try {
        localStorage.setItem(pageKey, JSON.stringify(checklist.map(item => item.checked)));
        storageAvailable = true;
      } catch (error) { storageAvailable = false; }
      // The existing listener reports session-only state; update after it runs.
      window.setTimeout(updateStatus, 0);
    }));
  }

  let shareDialog;
  let shareStatus;
  let shareText;
  function ensureShareDialog() {
    if (shareDialog) return shareDialog;
    shareDialog = document.createElement('dialog');
    shareDialog.id = 'warm-share-dialog';
    shareDialog.setAttribute('aria-labelledby', 'warm-share-title');
    shareDialog.innerHTML = '<form method="dialog"><button type="submit" aria-label="閉じる">閉じる</button></form>' +
      '<h2 id="warm-share-title">この市町村の案内を共有</h2>' +
      '<p>公開ページと公式出典を含む案内文をコピーできます。</p>' +
      '<textarea readonly rows="12" data-share-text aria-label="共有する案内文"></textarea>' +
      '<p role="status" aria-live="polite" data-share-status></p>' +
      '<button type="button" data-share-copy>案内文をコピー</button>' +
      '<button type="button" data-share-close>閉じる</button>';
    document.body.append(shareDialog);
    shareStatus = shareDialog.querySelector('[data-share-status]');
    shareText = shareDialog.querySelector('[data-share-text]');
    shareDialog.querySelector('[data-share-close]').addEventListener('click', () => shareDialog.close?.());
    shareDialog.querySelector('[data-share-copy]').addEventListener('click', async () => {
      const copied = await copyText(shareText.value);
      shareStatus.textContent = copied ? '案内文をコピーしました。' : 'コピーできませんでした。案内文を選択してコピーしてください。';
    });
    return shareDialog;
  }

  function shareContents() {
    const canonical = document.querySelector('link[rel="canonical"]')?.href;
    const pageUrl = canonical || location.href;
    const internalHosts = new Set([location.hostname]);
    try { if (canonical) internalHosts.add(new URL(canonical, location.href).hostname); } catch (error) {}
    const title = document.title || document.querySelector('h1')?.textContent?.trim() || pageUrl;
    const sources = [];
    const sourceLinks = [...document.querySelectorAll('main .sources a[href]')];
    const allMainLinks = [...document.querySelectorAll('main a[href]')];
    const candidates = [...sourceLinks, ...allMainLinks];
    candidates.forEach(link => {
      const url = link.href;
      let parsed;
      try { parsed = new URL(url, location.href); } catch (error) { return; }
      if (!/^https?:$/.test(parsed.protocol) || internalHosts.has(parsed.hostname)) return;
      if (sources.some(source => source.url === url) || sources.length >= 5) return;
      const item = link.closest('li') || link.parentElement;
      const date = item?.textContent?.match(/(?:確認日|内容の確認日)\s*[:：]\s*([0-9]{4}[-年][0-9]{1,2}[-月][0-9]{1,2}日?)/)?.[1];
      sources.push({ label: link.textContent.trim().replace(/\s+/g, ' '), url, date });
    });
    return `${title}\n${pageUrl}` + (sources.length ? `\n\n公式出典\n${sources.map(source => `・${source.label}${source.date ? `（確認日：${source.date}）` : ''}\n  ${source.url}`).join('\n')}` : '');
  }

  document.querySelectorAll('[data-share-city]').forEach(button => button.addEventListener('click', () => {
    const dialog = ensureShareDialog();
    shareText.value = shareContents();
    shareStatus.textContent = '';
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }));
})();
