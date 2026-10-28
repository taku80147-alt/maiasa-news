(function (host) {
  'use strict';
  // Fixed-date observances checked against the organising bodies. Other dates
  // use editorial conversation prompts, never invented commemorative days.
  const anniversaries = {
    '10-28': {
      name: '速記の日',
      question: 'メモは手書き派ですか？ それともスマホ派ですか？',
      source: '日本速記協会',
      url: 'https://sokki.or.jp/kyokai/activity/'
    },
    '10-29': {
      name: 'おしぼりの日',
      question: 'お店で温かいおしぼりが出てくると、ほっとしますよね。',
      source: '西日本貸おしぼり協同組合',
      url: 'https://www.oshibori.or.jp/72108/2021/10/05/10%E6%9C%8829%E6%97%A5%E3%81%AF/'
    },
    '11-01': {
      name: '紅茶の日',
      question: 'ひと息つくときは、コーヒー派ですか？ 紅茶派ですか？',
      source: '日本紅茶協会',
      url: 'https://www.tea-a.gr.jp/knowledge/tea_day/'
    },
    '11-08': {
      name: 'いい歯の日',
      question: '今日は「いい歯の日」だそうです。好きな食べ物を長く楽しみたいですね。',
      source: '日本歯科医師会',
      url: 'https://www.jda.or.jp/enlightenment/poster/iiha.html'
    },
    '11-11': {
      name: '介護の日',
      question: '今日は介護の日ですね。いつも現場を支えていただいて、ありがとうございます。',
      source: '厚生労働省',
      url: 'https://www.mhlw.go.jp/houdou/2008/07/h0728-2.html'
    }
  };
  const conversation = [
    ['お昼ごはんの話', 'この辺りで、お昼におすすめのお店はありますか？'],
    ['ひと息つくなら', 'ひと息つくとき、つい選んでしまう飲み物はありますか？'],
    ['小さな楽しみ', '最近、ちょっと楽しみにしていることはありますか？'],
    ['地元のおいしいもの', '地元の人に人気のお店って、どこですか？'],
    ['移動中のおとも', '移動中は音楽派ですか？ ラジオ派ですか？'],
    ['好きなパンの話', 'パン屋さんに行くと、つい買ってしまうパンは何ですか？'],
    ['ひと休みの工夫', '短い休憩でも気分が変わる、お気に入りの過ごし方はありますか？'],
    ['ごはんのおとも', 'これさえあればごはんが進む、というものはありますか？'],
    ['便利なもの', '最近使ってみて、これは便利だなと思ったものはありますか？'],
    ['甘いものの話', '甘いものなら、和菓子と洋菓子、どちらが好きですか？'],
    ['散歩の寄り道', '近くに、ちょっと歩くのに気持ちのいい場所はありますか？'],
    ['いつもの一杯', '飲み物は、いつもの味を選びますか？ 新しい味も試す方ですか？'],
    ['懐かしいおやつ', '子どもの頃によく食べたおやつって、何ですか？'],
    ['おにぎりの話', 'おにぎりの具で、結局いつも選んでしまうものは何ですか？'],
    ['ちょっとした気分転換', '気分を切り替えたいとき、何をすることが多いですか？'],
    ['本や雑誌の話', '最近、読んで面白かったものはありますか？'],
    ['おすすめの景色', 'この辺りで、眺めがいいなと思う場所はありますか？'],
    ['あたたかい一杯', 'ほっとしたいときに飲みたくなるものって、何ですか？'],
    ['休日のお昼', '休みの日のお昼は、外で食べる派ですか？ 家で食べる派ですか？'],
    ['文房具の話', '仕事で使うペンは、お気に入りの一本がありますか？'],
    ['音楽の話', '聞くと元気が出る曲って、ありますか？'],
    ['地元のおすすめ', '初めてこの街に来た人に、一つだけすすめるなら何ですか？'],
    ['いつもの買い物', '買い物はまとめて済ませる派ですか？ こまめに行く派ですか？'],
    ['季節の楽しみ', 'この季節になると、食べたくなるものはありますか？'],
    ['最近のお気に入り', '最近、つい人にすすめたくなったものはありますか？'],
    ['朝のひと息', '朝に少し余裕があるとき、何をして過ごしますか？'],
    ['地元の手みやげ', '気軽な手みやげを選ぶなら、この辺りでは何がおすすめですか？'],
    ['ほっとする味', '疲れた日に食べたくなる、ほっとする味は何ですか？'],
    ['いつか行きたい場所', '近場で、今度行ってみたいと思っている場所はありますか？'],
    ['好きな麺の話', '麺類なら、そば・うどん・ラーメン、どれが好きですか？'],
    ['今日の小さな発見', '最近「へえ」と思った、ちょっとした発見はありますか？']
  ];
  const seasonal = [
    ['お正月の味', 'お正月の食べ物で、毎年楽しみにしているものはありますか？'],
    ['冬の楽しみ', '寒い時季に食べたくなる、あたたかい料理は何ですか？'],
    ['春の気配', 'この辺りで、春を感じる場所はどこですか？'],
    ['春のお出かけ', '春に歩くなら、どの辺りがおすすめですか？'],
    ['新緑の季節', '緑がきれいな時季に、行きたくなる場所はありますか？'],
    ['雨の日の楽しみ', '雨の日を家で過ごすなら、何をして楽しみますか？'],
    ['夏の味', '夏になると食べたくなるものは、何ですか？'],
    ['涼しい時間の楽しみ', '夏の朝や夕方に、楽しみにしていることはありますか？'],
    ['秋の入口', '秋が来ると、何が楽しみになりますか？'],
    ['秋のおいしいもの', '秋の味覚で、いちばん楽しみなものは何ですか？'],
    ['あたたかい飲み物', 'あたたかい飲み物がおいしい季節ですね。お気に入りはありますか？'],
    ['年末の楽しみ', '年末になると、毎年楽しみにしていることはありますか？']
  ];

  function jstDate(now) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(now);
    const get = type => parts.find(p => p.type === type).value;
    return {year: get('year'), month: get('month'), day: get('day')};
  }

  function select(now = new Date()) {
    const d = jstDate(now), key = d.month + '-' + d.day;
    const fixed = anniversaries[key];
    const fallback = Number(d.day) === 1 ? seasonal[Number(d.month) - 1] : conversation[Number(d.day) - 1];
    return {
      date: d.year + '-' + key,
      dateLabel: new Intl.DateTimeFormat('ja-JP', {
        timeZone: 'Asia/Tokyo', month: 'numeric', day: 'numeric', weekday: 'short'
      }).format(now),
      kind: fixed ? 'anniversary' : 'conversation',
      title: fixed ? '今日は、' + fixed.name + '。' : fallback[0],
      question: fixed ? fixed.question : fallback[1],
      source: fixed ? fixed.source : '',
      sourceUrl: fixed ? fixed.url : ''
    };
  }

  function render(root, now = new Date()) {
    if (!root) return;
    const tip = select(now);
    root.dataset.date = tip.date;
    const date = root.querySelector('time');
    date.dateTime = tip.date;
    date.textContent = tip.dateLabel;
    root.querySelector('.today-title').textContent = tip.title;
    root.querySelector('.today-quote').textContent = '「' + tip.question + '」';
    const source = root.querySelector('.today-source');
    source.hidden = !tip.sourceUrl;
    if (tip.sourceUrl) {
      source.href = tip.sourceUrl;
      source.textContent = '出典：' + tip.source + ' ↗';
    } else {
      source.removeAttribute('href');
      source.textContent = '';
    }
  }

  const api = {select, render};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (host.document) {
    host.LivNaviToday = api;
    const refresh = () => {
      const root = host.document.getElementById('dailyTip');
      if (root && root.dataset.date !== select().date) render(root);
    };
    refresh();
    // No background cloud job or network call is required: the date chooses
    // stored editorial content. Reopened tabs and midnight use the same JST day.
    host.setInterval(refresh, 60000);
    host.document.addEventListener('visibilitychange', () => {
      if (!host.document.hidden) refresh();
    });
  }
})(typeof window !== 'undefined' ? window : globalThis);
(function (host) {
  'use strict';
  // Fixed-date observances checked against the organising bodies. Other dates
  // use editorial conversation prompts, never invented commemorative days.
  const anniversaries = {
    '10-28': {
      name: '速記の日',
      question: 'メモは手書き派ですか？ それともスマホ派ですか？',
      source: '日本速記協会',
      url: 'https://sokki.or.jp/kyokai/activity/'
    },
    '10-29': {
      name: 'おしぼりの日',
      question: 'お店で温かいおしぼりが出てくると、ほっとしますよね。',
      source: '西日本貸おしぼり協同組合',
      url: 'https://www.oshibori.or.jp/72108/2021/10/05/10%E6%9C%8829%E6%97%A5%E3%81%AF/'
    },
    '11-01': {
      name: '紅茶の日',
      question: 'ひと息つくときは、コーヒー派ですか？ 紅茶派ですか？',
      source: '日本紅茶協会',
      url: 'https://www.tea-a.gr.jp/knowledge/tea_day/'
    },
    '11-08': {
      name: 'いい歯の日',
      question: '今日は「いい歯の日」だそうです。好きな食べ物を長く楽しみたいですね。',
      source: '日本歯科医師会',
      url: 'https://www.jda.or.jp/enlightenment/poster/iiha.html'
    },
    '11-11': {
      name: '介護の日',
      question: '今日は介護の日ですね。いつも現場を支えていただいて、ありがとうございます。',
      source: '厚生労働省',
      url: 'https://www.mhlw.go.jp/houdou/2008/07/h0728-2.html'
    }
  };
  const conversation = [
    ['お昼ごはんの話', 'この辺りで、お昼におすすめのお店はありますか？'],
    ['ひと息つくなら', 'ひと息つくとき、つい選んでしまう飲み物はありますか？'],
    ['小さな楽しみ', '最近、ちょっと楽しみにしていることはありますか？'],
    ['地元のおいしいもの', '地元の人に人気のお店って、どこですか？'],
    ['移動中のおとも', '移動中は音楽派ですか？ ラジオ派ですか？'],
    ['好きなパンの話', 'パン屋さんに行くと、つい買ってしまうパンは何ですか？'],
    ['ひと休みの工夫', '短い休憩でも気分が変わる、お気に入りの過ごし方はありますか？'],
    ['ごはんのおとも', 'これさえあればごはんが進む、というものはありますか？'],
    ['便利なもの', '最近使ってみて、これは便利だなと思ったものはありますか？'],
    ['甘いものの話', '甘いものなら、和菓子と洋菓子、どちらが好きですか？'],
    ['散歩の寄り道', '近くに、ちょっと歩くのに気持ちのいい場所はありますか？'],
    ['いつもの一杯', '飲み物は、いつもの味を選びますか？ 新しい味も試す方ですか？'],
    ['懐かしいおやつ', '子どもの頃によく食べたおやつって、何ですか？'],
    ['おにぎりの話', 'おにぎりの具で、結局いつも選んでしまうものは何ですか？'],
    ['ちょっとした気分転換', '気分を切り替えたいとき、何をすることが多いですか？'],
    ['本や雑誌の話', '最近、読んで面白かったものはありますか？'],
    ['おすすめの景色', 'この辺りで、眺めがいいなと思う場所はありますか？'],
    ['あたたかい一杯', 'ほっとしたいときに飲みたくなるものって、何ですか？'],
    ['休日のお昼', '休みの日のお昼は、外で食べる派ですか？ 家で食べる派ですか？'],
    ['文房具の話', '仕事で使うペンは、お気に入りの一本がありますか？'],
    ['音楽の話', '聞くと元気が出る曲って、ありますか？'],
    ['地元のおすすめ', '初めてこの街に来た人に、一つだけすすめるなら何ですか？'],
    ['いつもの買い物', '買い物はまとめて済ませる派ですか？ こまめに行く派ですか？'],
    ['季節の楽しみ', 'この季節になると、食べたくなるものはありますか？'],
    ['最近のお気に入り', '最近、つい人にすすめたくなったものはありますか？'],
    ['朝のひと息', '朝に少し余裕があるとき、何をして過ごしますか？'],
    ['地元の手みやげ', '気軽な手みやげを選ぶなら、この辺りでは何がおすすめですか？'],
    ['ほっとする味', '疲れた日に食べたくなる、ほっとする味は何ですか？'],
    ['いつか行きたい場所', '近場で、今度行ってみたいと思っている場所はありますか？'],
    ['好きな麺の話', '麺類なら、そば・うどん・ラーメン、どれが好きですか？'],
    ['今日の小さな発見', '最近「へえ」と思った、ちょっとした発見はありますか？']
  ];
  const seasonal = [
    ['お正月の味', 'お正月の食べ物で、毎年楽しみにしているものはありますか？'],
    ['冬の楽しみ', '寒い時季に食べたくなる、あたたかい料理は何ですか？'],
    ['春の気配', 'この辺りで、春を感じる場所はどこですか？'],
    ['春のお出かけ', '春に歩くなら、どの辺りがおすすめですか？'],
    ['新緑の季節', '緑がきれいな時季に、行きたくなる場所はありますか？'],
    ['雨の日の楽しみ', '雨の日を家で過ごすなら、何をして楽しみますか？'],
    ['夏の味', '夏になると食べたくなるものは、何ですか？'],
    ['涼しい時間の楽しみ', '夏の朝や夕方に、楽しみにしていることはありますか？'],
    ['秋の入口', '秋が来ると、何が楽しみになりますか？'],
    ['秋のおいしいもの', '秋の味覚で、いちばん楽しみなものは何ですか？'],
    ['あたたかい飲み物', 'あたたかい飲み物がおいしい季節ですね。お気に入りはありますか？'],
    ['年末の楽しみ', '年末になると、毎年楽しみにしていることはありますか？']
  ];

  function jstDate(now) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(now);
    const get = type => parts.find(p => p.type === type).value;
    return {year: get('year'), month: get('month'), day: get('day')};
  }

  function select(now = new Date()) {
    const d = jstDate(now), key = d.month + '-' + d.day;
    const fixed = anniversaries[key];
    const fallback = Number(d.day) === 1 ? seasonal[Number(d.month) - 1] : conversation[Number(d.day) - 1];
    return {
      date: d.year + '-' + key,
      dateLabel: new Intl.DateTimeFormat('ja-JP', {
        timeZone: 'Asia/Tokyo', month: 'numeric', day: 'numeric', weekday: 'short'
      }).format(now),
      kind: fixed ? 'anniversary' : 'conversation',
      title: fixed ? '今日は、' + fixed.name + '。' : fallback[0],
      question: fixed ? fixed.question : fallback[1],
      source: fixed ? fixed.source : '',
      sourceUrl: fixed ? fixed.url : ''
    };
  }

  function render(root, now = new Date()) {
    if (!root) return;
    const tip = select(now);
    root.dataset.date = tip.date;
    const date = root.querySelector('time');
    date.dateTime = tip.date;
    date.textContent = tip.dateLabel;
    root.querySelector('.today-title').textContent = tip.title;
    root.querySelector('.today-quote').textContent = '「' + tip.question + '」';
    const source = root.querySelector('.today-source');
    source.hidden = !tip.sourceUrl;
    if (tip.sourceUrl) {
      source.href = tip.sourceUrl;
      source.textContent = '出典：' + tip.source + ' ↗';
    } else {
      source.removeAttribute('href');
      source.textContent = '';
    }
  }

  const api = {select, render};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (host.document) {
    host.LivNaviToday = api;
    const refresh = () => {
      const root = host.document.getElementById('dailyTip');
      if (root && root.dataset.date !== select().date) render(root);
    };
    refresh();
    // No background cloud job or network call is required: the date chooses
    // stored editorial content. Reopened tabs and midnight use the same JST day.
    host.setInterval(refresh, 60000);
    host.document.addEventListener('visibilitychange', () => {
      if (!host.document.hidden) refresh();
    });
  }
})(typeof window !== 'undefined' ? window : globalThis);
