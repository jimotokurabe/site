"""Build conservative four-route research drafts from the archived official pages."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
DATE = "2026-10-18"
FIELDS = ("waste_scope", "collection_location", "indoor_carry", "eligibility",
          "family_help", "fees", "limits", "application", "attendance", "contact")
KINDS = ("daily_support", "bulky_carry_support", "regular_bulky", "self_dropoff")
NAMES = {
    "yamaguchi": ("yamaguchi", "山口市", "やまぐちし", "山口県"),
    "tokushima": ("tokushima", "徳島市", "とくしまし", "徳島県"),
    "kagawa": ("takamatsu", "高松市", "たかまつし", "香川県"),
    "ehime": ("matsuyama", "松山市", "まつやまし", "愛媛県"),
    "kochi": ("kochi", "高知市", "こうちし", "高知県"),
    "saga": ("saga", "佐賀市", "さがし", "佐賀県"),
    "nagasaki": ("nagasaki", "長崎市", "ながさきし", "長崎県"),
    "kumamoto": ("kumamoto", "熊本市", "くまもとし", "熊本県"),
    "oita": ("oita", "大分市", "おおいたし", "大分県"),
    "miyazaki": ("miyazaki", "宮崎市", "みやざきし", "宮崎県"),
    "kagoshima": ("kagoshima", "鹿児島市", "かごしまし", "鹿児島県"),
    "okinawa": ("naha", "那覇市", "なはし", "沖縄県"),
}
FOLDER = {"kagawa":"takamatsu", "ehime":"matsuyama", "okinawa":"naha"}


def folder(slug):
    return FOLDER.get(slug, slug)

# Values here are grounded in the corresponding saved official text; unspecified fields
# deliberately remain unknown for office confirmation.
FACTS = {
 "yamaguchi": {
  "daily_support": {
   "name":"ごみ出し支援事業（実証中）","src":"daily",
   "waste_scope":"燃やせるごみを週1回収集。","collection_location":"玄関先等の屋外に出されたごみを収集。屋内からの運び出しではない。",
   "eligibility":{"all":["世帯員全員が山口市に住所を有し居住","世帯員全員が要介護1以上の認定者または身体・療育・精神のいずれかの障害者手帳所持者","世帯員自身も別居親族・介護関係者等の支援でもステーションへの排出が困難と認められる"]},
   "family_help":"別居親族や介護関係者等による排出も困難なこと。","fees":"利用料金は無料。","limits":"実証中。燃やせるごみのみ週1回。","application":"ケアマネジャー等から事前相談後、申請・訪問調査・決定通知。代理申請可。","contact":"山口市清掃事務所 083-927-1770。",
   "questions":["実証中の募集・対象区域と終了予定を確認してください。","親族・介護サービスの支援がどこまであれば対象外になるか確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ戸別収集","src":"regular","waste_scope":"指定袋に入らない燃やせるごみ、一辺1m以上の燃やせないごみ・金属・小型家電。","collection_location":"2t収集車が進入・転回でき、作業に支障のない屋外。","indoor_carry":"市の収集作業員は屋内搬出を行わない。","fees":"有料。品目別処理手数料を事前決済または市窓口で支払う。","limits":"一辺2m超または50kg超は収集不可。1回おおむね10個以内。","application":"ネットはオンライン決済、電話は083-941-0053へ予約し市窓口で支払う。","attendance":"収集日の立会い不要。","contact":"山口市清掃事務所 083-941-0053。"},
  "self_dropoff":{"name":"家庭ごみの処理施設への持込","src":"dropoff","waste_scope":"家庭ごみは種類に応じ市の持込施設へ搬入できる。","collection_location":"ごみの種類で持込施設が異なる。","application":"各持込施設の受入条件を事前に確認する。"},
 },
 "tokushima": {
  "daily_support":{"name":"ふれあい収集","src":"daily","waste_scope":"可燃・不燃・プラマーク・缶びん・ペットボトル・古紙を収集。","collection_location":"原則、玄関先または門扉先。","eligibility":{"all":["親族・近隣のごみ出し協力を得られない"],"any":["65歳以上で要支援2以上","身体障害者手帳1級または2級","療育手帳A1またはA2"]},"family_help":"親族・近隣の協力が得られないこと。","application":"環境政策課窓口へ申請。代理申請可。","contact":"徳島市環境政策課 088-621-5202・5206・5217。","questions":["世帯内に対象外の同居者がいる場合の扱いを確認してください。","収集頻度・費用・立会いを確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ申込収集","src":"regular","collection_location":"収集通知書に記載された場所へ当日8時30分までに排出。","application":"専用はがきまたはインターネットで申込。","limits":"年6回の地区別申込月。1世帯各申込月1回・大小計5個まで。","fees":"市から届く粗大ごみ収集シールを貼る方式。別途手数料の記載は確認原典にない。"},
  "self_dropoff":{"name":"ごみ処理施設への持込","src":"dropoff","waste_scope":"種類別に分別して各施設へ持込。","application":"持込前に各施設へ問い合わせる。","fees":"重量に応じた処理手数料。"},
 },
 "kagawa": {
  "daily_support":{"name":"たかまつごみ出しサポート事業（第2期実証）","src":"daily","waste_scope":"ステーションに出せる家庭ごみ全種。粗大ごみを除く。","collection_location":"市職員が玄関先へ収集。","eligibility":{"all":["対象地区に居住","自力でステーションに出せず家族・地域の支援がない","世帯員が全員65歳以上で要介護1以上","居宅サービス利用"]},"family_help":"家族・地域によるごみ出し支援が受けられないこと。","fees":"1回510円。臨時・粗大ごみ処理シール1枚。","limits":"令和7年9月1日から令和8年12月31日予定。対象地区限定。1回3袋・各袋10kg以内。収集希望日の2営業日前までに電話依頼。","application":"利用申請後、市職員が自宅を訪問し可否決定。代理申請可。","questions":["住所が第2期実証の対象地区か、令和8年末以降の継続方針を確認してください。","訪問型サービスBと居宅サービスの扱いを確認してください。"]},
  "regular_bulky":{"name":"臨時・粗大ごみ戸別収集","src":"regular","waste_scope":"ステーションに出せない臨時・粗大ごみ。","collection_location":"収集車が入れる所まで搬出。","indoor_carry":"市の通常収集では収集車が入れる所への搬出が必要。","fees":"有料。受付で品目別金額を確認し510円単位の処理シールを購入。","application":"粗大ごみ受付センターへ電話またはネット申込。","attendance":"通常は立会い不要。家電リサイクル対象品は立会い必要。","limits":"予約から収集まで通常7～10日程度。"},
  "self_dropoff":{"name":"臨時・粗大ごみ自己搬入","src":"dropoff","waste_scope":"臨時・粗大ごみを分別し処理施設へ自己搬入。","fees":"施設での処理手数料は収集シールとは別。","application":"ごみの種類に応じ搬入先・時間を確認する。"},
 },
 "ehime": {
  "daily_support":{"name":"ふれあい収集","src":"daily","waste_scope":"可燃、ペットボトル、プラ容器、紙類、金物・ガラス、埋立、水銀ごみ。","collection_location":"玄関先等に置く貸与のふた付きごみ箱から週1回収集。","eligibility":{"all":["世帯全員がごみ出し困難","世帯全員が次のいずれか：65歳以上かつ要介護1以上、または65歳以上かつ身体障害者手帳1・2級"]},"application":"本人か代理人が清掃課へ連絡し、市職員が訪問調査。","contact":"松山市清掃課 089-921-5516。","questions":["要綱の親族・近隣協力要件と例外を窓口確認してください。","集合住宅の設置場所・立会い・費用を確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ戸別収集","src":"regular","waste_scope":"松山・北条地域の粗大ごみ。中島地域は出し方が異なる。","application":"松山・北条地域はハガキまたはネット申込。","limits":"松山・北条地域は地区別の申込期間に従う。","collection_location":"通知された場所へ収集日朝までに排出。"},
  "self_dropoff":{"name":"粗大ごみ等の直接搬入","src":"dropoff","waste_scope":"品目・地域で施設を分ける。南クリーンセンターは可燃ごみと粗大ごみ、西は可燃性粗大のみ。","fees":"重量により手数料がかかる。","application":"品目と搬入先を市の案内で確認する。"},
 },
 "kochi": {
  "daily_support":{"name":"高知市ふれあい収集","src":"daily","waste_scope":"可燃ごみ・プラスチック製容器包装。","collection_location":"訪問による玄関先からの収集。","eligibility":{"all":["市内の居宅で生活","自力で持ち出せず親族・近隣の協力を得られない"],"any":["70歳以上で要介護1以上の単身世帯","身体障害者手帳を持つ単身世帯","精神障害者保健福祉手帳を持つ単身世帯","療育手帳を持つ単身世帯","その他、市が困難と認める世帯"],"exception":"同居者がいても、対象条件に該当する世帯員のみで構成される場合は対象"},"family_help":"親族・近隣の協力を得られないこと。","application":"申請書で環境業務課へ申請。","contact":"高知市環境業務課 088-856-5374。"},
  "regular_bulky":{"name":"可燃粗大ごみの通常排出","src":"regular","waste_scope":"燃える素材で45L袋に入らない可燃粗大ごみ。","collection_location":"市の分別案内に従い所定の場所へ出す。","questions":["可燃粗大と不燃・資源の大型品の排出方法を確認してください。"]},
  "self_dropoff":{"name":"清掃工場への可燃ごみ持込","src":"dropoff","waste_scope":"高知市内発生の可燃ごみ・可燃粗大ごみのみ。","collection_location":"高知市清掃工場。","eligibility":"原則、排出者本人または家族が搬入。","family_help":"家族による代理搬入を公式FAQで明示。","fees":"2026年4月1日から10kgまでごとに130円。","application":"受付日・時間を確認して搬入。","questions":["本人と家族が同乗する際の荷下ろし補助・本人確認を確認してください。"]},
 },
 "saga": {
  "regular_bulky":{"name":"粗大ごみ定期収集","src":"regular","waste_scope":"家庭の粗大ごみを月1回の指定日に収集。","collection_location":"指定場所へ収集日8時30分までに排出。","application":"佐賀市ごみ予約センターへ電話またはネット申込。","fees":"品目に応じ処理手数料を支払う。","questions":["定期収集の品目・地区別収集日・室内搬出の有無を確認してください。"]},
  "bulky_carry_support":{"name":"粗大ごみ臨時収集時の別料金搬出相談","src":"carry","waste_scope":"粗大ごみ・一時多量ごみ。","collection_location":"2tトラックが横付けでき道路から見える場所。","indoor_carry":"基本処理手数料に室内搬出は含まれない。収集業者へ頼む場合は別途料金を相談。","fees":"積込量に応じた処理手数料。室内搬出は別料金。","application":"地区担当の市委託収集業者へ直接電話予約。","limits":"希望日の少なくとも1週間前に申込。繁忙期は予約困難。","questions":["住所の担当業者が室内搬出を受けるか、見積り・立会い・搬出対象を確認してください。"]},
  "self_dropoff":{"name":"佐賀市清掃工場への直接搬入","src":"dropoff","waste_scope":"市の受入対象となる家庭ごみ。","collection_location":"佐賀市清掃工場。場内では係員の指示に従い自分で荷下ろし。","fees":"指定袋のごみのみ、紙・布類のみ、蛍光管のみの持込は手数料不要。その他の料金は重量等を確認。","application":"土曜・祝日は事前予約。","questions":["親族による代理搬入の扱いを確認してください。"]},
 },
 "nagasaki": {
  "daily_support":{"name":"ふれあい訪問収集","src":"daily","waste_scope":"ごみステーションへの排出が常時困難な方の家庭ごみ。","collection_location":"自宅へ訪問して戸別収集。","eligibility":{"any":["65歳未満で身体障害者手帳を持つ単身者","65歳未満で特定疾患医療受給者証を持つ単身者","前2者とおおむね65歳以上の高齢者だけの世帯"],"note":"65歳以上の方の条件は各総合事務所の案内を別途確認"},"application":"65歳以上は各総合事務所へ、65歳未満の該当者は障害福祉課へ申請。","questions":["65歳以上の対象資格と世帯条件を所管窓口で確認してください。","日常収集の品目・頻度・費用を確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ収集","src":"regular","waste_scope":"長さ2m未満・重さ60kg未満等の粗大ごみ。","application":"電話095-801-2200。対象13品目はネット申込も可（対象拡大中）。","limits":"1回2個まで。収集まで通常1～2週間。","fees":"2026年4月改定の品目別ステッカー購入。","contact":"長崎市粗大ごみ収集受付センター 095-801-2200。"},
  "self_dropoff":{"name":"廃棄物の自己搬入","src":"dropoff","waste_scope":"長崎市内の家庭系一般廃棄物等。","eligibility":"原則、排出者本人または親族が搬入。","family_help":"親族による搬入は可。搬入券の他人への譲渡不可。","fees":"10kgまでごとに80円。","application":"搬入券の交付を受け、1か月以内に施設へ搬入。"},
 },
 "kumamoto": {
  "daily_support":{"name":"ふれあい収集","src":"daily","waste_scope":"定期収集対象の家庭ごみ。大型ごみは対象外。","collection_location":"玄関前。オートロック住宅は利用者が開錠し、在宅時に収集。","indoor_carry":"家の中には入れず、取り決めた屋外の場所まで排出が必要。","eligibility":{"all":["本人と同居者全員が次のいずれかに該当","ステーション排出が難しい","他の協力を得られない"],"any":["要介護1～5","身体障害者手帳1・2級の肢体不自由または視覚障害","精神障害者保健福祉手帳1級","療育手帳A","加齢や傷病等で排出困難と市が認める"]},"family_help":"他の協力を得られないこと。","limits":"原則1人につき45L袋2袋相当まで。3人以上の世帯は5袋相当まで。大型ごみ不可。","application":"各区総務企画課へ申請書と区分別の証明書を提出し、市の調査・審査後に決定。","contact":"熊本市廃棄物計画課 096-328-2359。","questions":["植木地区の出し方、オートロックの在宅要件を確認してください。","市長が認める例外の証明書と、同居者全員の条件を確認してください。"]},
  "regular_bulky":{"name":"大型ごみ戸別収集","src":"regular","waste_scope":"植木地区を除き、指定大袋に入れて口を結べない家庭ごみ等。","application":"ごみゼロコールへ電話予約。","limits":"原則1回5個まで。予約から通常1週間、繁忙期は3週間程度。","fees":"品目ごと500円または900円の処理シール。","contact":"ごみゼロコール 0570-00-5374。"},
  "self_dropoff":{"name":"熊本市処理施設への持込","src":"dropoff","waste_scope":"品目に応じ東部・西部環境工場、扇田環境センターへ持込。","fees":"一般廃棄物10kgまでごとに150円。指定袋入りも手数料対象。","application":"品目に応じた施設の受入条件を確認。"},
 },
 "oita": {
  "daily_support":{"name":"高齢者等世帯に対するごみ出し支援","src":"daily","waste_scope":"市が定期収集する家庭ごみ。一時的多量ごみは対象外。","collection_location":"玄関先等に出されたごみを週1回収集。","eligibility":{"all":["世帯全員が自力でステーションに運べない","親族・近隣等の協力が困難","世帯全員が次のいずれか：65歳以上かつ要介護1以上で訪問介護の生活援助利用、障害福祉サービス受給者で居宅介護または重度訪問介護利用、市長の特認"]},"family_help":"親族・近隣等の協力が困難なこと。","application":"申請書と必要書類を提出、現地調査・可否決定。","contact":"大分市清掃業務課 097-568-5763。","questions":["対象者区分と必要書類、現地調査時に立ち会える人を確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ・一時多量ごみ有料収集","src":"regular","waste_scope":"大型家具や一時的多量ごみ。資源物・生ごみは対象外。","collection_location":"収集車が横付けできる屋外。集合住宅は駐車場・ステーション付近または1階屋外。","indoor_carry":"市職員は屋内から搬出しない。","fees":"量に応じ有料。","application":"居住校区の担当事業所へ電話予約。多量なら下見。","attendance":"収集当日の立会い必要。"},
  "self_dropoff":{"name":"処理施設への自己持込","src":"regular","waste_scope":"市の施設で受け入れる家庭ごみ。","fees":"量により料金が決まる。","application":"事前申込不要。品目と施設の受入条件を確認。"},
 },
 "miyazaki": {
  "daily_support":{"name":"特別な事情がある世帯の戸別収集相談","src":"daily","waste_scope":"一般の新規戸別収集は原則認めていない。特別な事情があれば個別相談。","eligibility":"集積所に出せない特別な事情がある場合。正式な制度利用条件は確認資料に記載なし。","application":"まず自治会に相談し、その上で宮崎市環境業務課へ連絡。","questions":["足が悪い場合などの戸別相談が実際に可能か、決定基準・頻度・費用を確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ申込収集","src":"regular","waste_scope":"宮崎市の収集対象となる粗大ごみ。","application":"宮崎市コールセンターへ電話、またはオンライン受付後に市からの電話確認で申込完了。","limits":"1回3点まで。収集は受付後通常7～14日。","fees":"品目別手数料を粗大ごみシール（1枚500円）で納付。","collection_location":"収集日8時30分までに指定場所へ出す。"},
  "self_dropoff":{"name":"エコクリーンプラザみやざきへの家庭ごみ搬入","src":"dropoff","waste_scope":"宮崎市・国富町・綾町の家庭から出た受入対象ごみ。","eligibility":"排出者本人または同居親族、もしくは許可業者。","family_help":"同居親族の搬入可。別居親族の扱いは要確認。","fees":"2025年4月から家庭ごみ100kgごとに660円（100kg未満も660円）。","application":"搬入者の氏名・住所・電話番号を確認。状況により身分証確認。","questions":["別居家族の代理搬入は受入対象か確認してください。"]},
 },
 "kagoshima": {
  "daily_support":{"name":"まごころ収集","src":"daily","waste_scope":"家庭ごみ・資源物の戸別収集。","eligibility":{"all":["本人が自力でごみを排出できず他の協力も得られない","介護保険法または障害者総合支援法の居宅サービス利用","単身者は市の介護・障害条件のいずれか、または対象者のみで構成する世帯"]},"family_help":"他にごみ出し協力を得られないこと。","application":"まず清掃事務所へ電話相談後、申請書と手帳・介護保険証等の写しを提出。","contact":"鹿児島市清掃事務所 099-238-0201。","questions":["同居者全員の対象区分と居宅サービス利用条件を確認してください。","収集頻度・費用・屋外排出位置を確認してください。"]},
  "bulky_carry_support":{"name":"粗大ごみ家屋内収集","src":"regular","waste_scope":"屋外に運び出せない粗大ごみを家屋内から収集。","collection_location":"家屋内からの搬出。","indoor_carry":"対象世帯は市の作業員が家屋内へ入って収集。","eligibility":{"all":["自ら屋外に運び出すことが困難","世帯員全員が65歳以上、指定の障害者、要介護3～5のいずれかに該当"]},"limits":"申込から収集まで約2か月。1世帯1回5点までの通常粗大ごみ申込上限に注意。","attendance":"家屋内収集は立会い必要。","application":"粗大ごみ受付へ申込、事前に要件確認。","questions":["品目別の屋内搬出可否、家屋の作業条件、手数料を確認してください。"]},
  "regular_bulky":{"name":"粗大ごみ通常収集","src":"regular","waste_scope":"家庭の粗大ごみ。","collection_location":"通常は家の前など指定場所へ運び出す。","fees":"品目別の処理手数料券またはWeb申込時のキャッシュレス決済。","limits":"1世帯1回5点まで。申込から約2週間。","application":"Webまたは電話申込。","attendance":"通常の屋外収集は立会い不要。家屋内収集は必要。"},
  "self_dropoff":{"name":"北部清掃工場への粗大ごみ持込","src":"regular","waste_scope":"北部清掃工場の粗大ごみ処理棟への持込。南部は粗大ごみ不可。","collection_location":"鹿児島市犬迫町11900番地の北部清掃工場。","application":"搬入者と排出場所の確認書類を提示。品目によっては事前連絡。","contact":"北部清掃工場 099-238-0211。"},
 },
 "okinawa": {
  "daily_support":{"name":"アシスト収集","src":"daily","waste_scope":"高齢者等のごみ出し困難世帯への戸別訪問収集。","collection_location":"計画には玄関等での収集と記載。","eligibility":"高齢者で日常のごみ出しができない世帯を対象とする計画記載。具体的な申請条件は確認原典に記載なし。","application":"現行の募集・申請案内を未取得。クリーン推進課へ確認が必要。","questions":["アシスト収集の現行申請ページ・対象条件・対象品目・費用・頻度を確認してください。","計画資料の記述を現行制度の全条件として扱わないでください。"]},
  "regular_bulky":{"name":"そ大ごみ・スプリング入り製品収集","src":"regular","waste_scope":"市の分類によるそ大ごみとスプリング入り製品。","application":"ネットまたはクリーン推進課へ電話で申込。","contact":"那覇市クリーン推進課 098-889-3567。","fees":"そ大ごみ処理券。スプリング入り製品は別の適正処理困難物処理券。"},
  "self_dropoff":{"name":"ごみの処理施設への持込","src":"dropoff","waste_scope":"家庭ごみと資源化物は品目別の施設へ搬入。","fees":"家庭ごみは10kgまでごとに60円。資源化物は無料。スプリング入り製品は別料金。","application":"品目別の持込先と事前受付の要否を確認。"},
 },
}

ROUTE_NAME = {
 "daily_support":"日常のごみ出し支援",
 "bulky_carry_support":"粗大ごみの室内搬出支援",
 "regular_bulky":"通常の粗大ごみ収集",
 "self_dropoff":"処理施設への自己搬入",
}
CITY_QUESTIONS = {
 "yamaguchi":[
  "実証中のごみ出し支援が阿東・徳地などを含む住所でも利用できるか確認してください。",
  "粗大ごみを屋内から出せない場合、市の支援または適法な許可業者の相談先を確認してください。",
  "収集車が自宅前で転回できないときの排出場所と、10個程度を超える場合の扱いを確認してください。",
  "大型品を持ち込む車両・家族同伴の条件と、品目別持込先を確認してください。"],
 "tokushima":[
  "ふれあい収集の世帯員全員の条件、対象外同居者がいる場合、声かけの選択を確認してください。",
  "玄関先まで運べない粗大ごみに室内搬出の市制度があるか確認してください。",
  "お住まいの地区の偶数・奇数申込月と、5点超の次回申込を確認してください。",
  "粗大ごみの材質ごとの搬入先と計量料金を各施設に確認してください。"],
 "kagawa":[
  "居住地が第2期対象地区か、年末予定後も支援を継続するか確認してください。",
  "要介護世帯が粗大ごみを収集車の入る場所まで出せない場合の相談先を確認してください。",
  "510円券が複数枚必要な品目の見積りと家電4品目の立会いを確認してください。",
  "自己搬入は収集シールを使用できないため、施設別料金と受入品目を確認してください。"],
 "ehime":[
  "中島地域のふれあい収集に同じ資格・品目が適用されるか確認してください。",
  "ふれあい収集利用者が粗大ごみを室内から出せない場合の支援先を確認してください。",
  "松山・北条地域の住所ごとのハガキ申込期間と年6回の利用上限を確認してください。",
  "不燃性粗大ごみは西クリーンセンターで受け入れないため、品目別施設を確認してください。"],
 "kochi":[
  "単身条件の例外と、同居者がいる場合の全員資格を環境業務課へ確認してください。",
  "可燃粗大ごみを運び出せない世帯への搬出支援の有無を確認してください。",
  "可燃粗大と不燃性大型品で通常の出す場所・収集日がどう異なるか確認してください。",
  "別居家族が本人のごみを搬入するときの必要書類を清掃工場へ確認してください。"],
 "saga":[
  "市の日常ごみ出し戸別支援の実施有無を福祉・清掃双方の担当窓口へ確認してください。",
  "臨時収集の地区担当業者が室内搬出を受ける場合、別料金の見積りと作業範囲を確認してください。",
  "定期収集の翌月指定日とステッカー方式の申込期限・品目別料金を確認してください。",
  "土曜・祝日の清掃工場予約と、本人以外の家族が運ぶ場合の条件を確認してください。"],
 "nagasaki":[
  "65歳以上の方は総合事務所で資格・同居条件・申請書類を確認してください。",
  "斜面地の住まいで屋外へ粗大ごみを出せない場合の搬出方法を確認してください。",
  "2個上限と2026年4月改定ステッカー料金、ネット対象品目を受付センターへ確認してください。",
  "搬入券の1か月期限、親族による搬入、持込先の材質別受入を確認してください。"],
 "kumamoto":[
  "同居者全員の資格と、加齢・傷病の特認に必要な意見書を確認してください。",
  "大型ごみはふれあい収集対象外のため、室内から出せない場合の相談先を確認してください。",
  "植木地区の大型ごみの別ルール、5個上限、繁忙期の予約日を確認してください。",
  "東部・西部・扇田の品目別施設と、指定袋入りも計量料金対象になる点を確認してください。"],
 "oita":[
  "訪問介護の生活援助または障害福祉の居宅介護利用の証明を確認してください。",
  "日常支援と別の有料収集で、室内の大型家具を運び出す方法を確認してください。",
  "住居の校区担当事業所と、当日の立会い・トラック横付け位置を確認してください。",
  "自己持込時の施設別分別と重量料金、荷下ろし補助の有無を確認してください。"],
 "miyazaki":[
  "自治会相談後の個別戸別収集が可能となる特別事情と判断者を環境業務課に確認してください。",
  "通常の粗大ごみを屋内から搬出できないときの市相談先を確認してください。",
  "オンライン受付は後日の電話確認まで完了しないため、連絡時期と3点上限を確認してください。",
  "別居家族の代理搬入可否と本人が亡くなった場合の事前連絡手順を確認してください。"],
 "kagoshima":[
  "谷山・喜入地区は南部清掃工場、それ以外は清掃事務所へ、同居者条件を確認してください。",
  "家屋内収集の障害等級と要介護3～5、搬出経路・立会いを確認してください。",
  "通常収集の5点上限と約2週間、家屋内収集の約2か月を区別して予約してください。",
  "北部清掃工場の持込書類と、建材等の事前連絡対象を確認してください。"],
 "okinawa":[
  "アシスト収集の現行申請窓口と資格は計画資料だけでは足りないため確認してください。",
  "アシスト収集の粗大・多量ごみへの対応は計画上の検討であり、現在の制度を確認してください。",
  "スプリング入り製品の別券と通常そ大ごみの収集位置を確認してください。",
  "那覇・南風原クリーンセンターの事前受付とエコマール那覇の品目を確認してください。"],
}


def build_field(value, ids, state=None):
    return {"value":value, "state":state or ("explicit" if value is not None else "not_stated"), "source_ids":ids}


prepared = []
held = []
for slug, (city_id, city_name, kana, pref_name) in NAMES.items():
    dest = folder(slug)
    meta = json.loads((ROOT / dest / "official-metadata.json").read_text())
    bykey = {r["id"].split("-", 1)[1]:r["id"] for r in meta}
    services = []
    for kind in KINDS:
        fact = FACTS[slug].get(kind)
        if fact:
            key = fact["src"]
            evidence = "official_listing"
            name = fact["name"]
            source_ids = [bykey[key]]
        else:
            evidence = "searched_not_found"
            name = ROUTE_NAME[kind] + "（制度案内未確認）"
            source_ids = [r["id"] for r in meta if any(k in r["id"] for k in ("daily", "regular"))]
            fact = {"questions":[f"{city_name}にこの経路の現行制度があるか、担当窓口へ確認してください。"]}
        fields = {}
        for field in FIELDS:
            val = fact.get(field)
            if val is None:
                val = "確認した公式原典に記載なし。窓口で確認が必要。"
                state = "not_stated"
            elif evidence == "searched_not_found":
                state = "not_found"
            else:
                state = "explicit"
            fields[field] = build_field(val, source_ids, state)
        if kind == "bulky_carry_support" and evidence == "searched_not_found":
            fields["indoor_carry"] = build_field(
                "確認した公式案内から市の室内搬出支援制度は特定できない。制度なしとの断定ではない。",
                source_ids, "not_found")
        questions = fact.get("questions", [])
        specific = CITY_QUESTIONS[slug][KINDS.index(kind)]
        if specific not in questions:
            questions.append(specific)
        services.append({
            "id":f"{city_id}-{kind.replace('_','-')}", "kind":kind, "name":name,
            "evidence_status":evidence, "review_status":"ai_draft",
            "ai_reviewed_at":None, "human_reviewed_at":None, "checked":DATE,
            "fields":fields, "questions_for_office":questions,
        })
    city = {
        "id":f"{slug}:{city_id}", "name":city_name, "kana":kana, "pref_name":pref_name,
        "selection_reason":"全国47都道府県のごみ支援入口として、未掲載県から県庁所在市を1市選定。",
        "publication_status":"research_only", "services":services,
        "priority_notes":"4経路は別制度。資格のAND/OR、親族条件、地域差、室内搬出の有無を混同しない。未記載は窓口確認。",
        "common_questions_for_office":[
            f"{city_name}の住居地区で各経路を利用できるか",
            "申込者・同居者・別居家族の資格と代理搬入・代理申請の可否",
            "費用・減免・品目・点数・収集日・立会い・搬出位置",
        ],
    }
    data = {
        "schema_version":"research-0.1", "checked":DATE, "human_reviewed":False,
        "ai_draft":True, "draft":True, "not_for_publication":True,
        "cities":[city], "sources":meta,
        "research_note":"2026-10-18取得の自治体公式原典に基づくAI調査草稿。各原典のraw/text/SHA-256はofficial-metadata.jsonを参照。記載なし・検索未発見は制度不存在や無料を意味しない。独立レビュー、人手原文確認、窓口確認、公開承認は未実施。",
    }
    output = ROOT / dest / "new-city.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    prepared.append({"slug":dest,"sha256":digest})
    locators = []
    for service in services:
        records = []
        for source_id in sorted({sid for fld in service["fields"].values() for sid in fld["source_ids"]}):
            source = next(r for r in meta if r["id"] == source_id)
            line_count = len((ROOT / source["text_file"]).read_text().splitlines())
            records.append({
                "id":source_id, "path":str((ROOT / source["text_file"]).resolve()),
                "lines":[[1,line_count]], "raw_path":source["raw_file"],
                "raw_sha256":source["raw_sha256"], "text_sha256":source["text_sha256"],
                "field_names":[key for key, val in service["fields"].items() if source_id in val["source_ids"]],
            })
        locators.append({
            "city":f"{slug}:{city_id}", "service":service["id"],
            "service_sha256":hashlib.sha256(json.dumps(service,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            "sources":records,
        })
    (ROOT / dest / "review-locators.json").write_text(json.dumps(locators,ensure_ascii=False,indent=2)+"\n")
    note = "\n".join([
        f"# {city_name} ごみ支援調査（2026-10-18）",
        "",
        f"自治体公式原典{len(meta)}件を実取得し、原本と抽出テキストをofficial/に保存。URL・取得時刻・HTTP状態・SHA-256はofficial-metadata.json。",
        "4経路×10項目のAI下書きはnew-city.json。未記載は不明として保持し、制度の不在や無料と断定しない。独立AIレビュー・人手原文全件確認・窓口確認・公開承認は未実施。",
        "",
        "## 原典内の確認位置",
        *[f"- {r['id']}: official/{Path(r['text_file']).name}、見出し「{r['title']}」" for r in meta],
        "",
        "## 優先確認",
        *[f"- {s['name']}: " + " / ".join(s["questions_for_office"]) for s in services],
        "",
    ])
    (ROOT / dest / "README.md").write_text(note)
    if slug in ("kagawa", "saga", "miyazaki", "okinawa"):
        reason = {
            "kagawa":"日常支援は地区限定・2026年12月末までの第2期実証であり継続未確認。",
            "saga":"日常の市営戸別支援を公式原典で特定できていない。",
            "miyazaki":"日常は個別相談案内で、制度の可否・条件が未確認。",
            "okinawa":"アシスト収集は計画資料のみで現行の申請・資格一次案内が不足。",
        }[slug]
        held.append({"slug":dest,"reason":reason})
    print(slug, digest)

(ROOT / "group-west.json").write_text(json.dumps({
    "checked":DATE,"prepared":prepared,"held":held,
    "consumption":{"model_tokens":"unavailable","credits":"unavailable","source_requests":37,"unique_official_sources":sum(len(json.loads((ROOT / folder(s) / "official-metadata.json").read_text())) for s in NAMES),"note":"12市の公式原典36件を保存。熊本の一覧ページを1回取得後、本文ページへ差し替えて再取得したためHTTP取得は計37回。独立レビュー未実施。"}
},ensure_ascii=False,indent=2)+"\n")
