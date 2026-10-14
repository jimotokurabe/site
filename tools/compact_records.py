"""Presentation-only rules; source JSON and verification dates are never edited."""
import re

EMPTY_VALUES = {'記載なし', '未記録'}
RETURN_PRESENT = {'give', 'discount', 'elder', 'purchase'}
TAXI_PRESENT = {'yes', 'care', 'henno_only', 'active', 'document_checked'}
BUS_PRESENT = {'active', 'document_checked', 'henno'}


def has_sources(record):
    if not isinstance(record, dict):
        return False
    if any(isinstance(record.get(k), str) and record[k].startswith(('https://', 'http://'))
           for k in ('url', 'source', 'src_url', 'link_url')):
        return True
    return any(has_sources(x) for x in record.get('sources', []) if isinstance(x, dict))


def unsupported_negative(record, field, value):
    """Only omit a source-free, single-sentence negative placeholder.

    Multi-sentence explanations (e.g. alternatives, exclusions or conditions)
    remain verbatim even when no source URL was recorded.
    """
    return (field == 'what' and record.get('k') == 'notfound' and not has_sources(record)
            and isinstance(value, str) and value.count('。') == 1
            and bool(re.search(r'(?:見つかりませんでした|確認できませんでした)。$', value))
            and not re.search(r'ただし|一方|ですが|ますが|あるが|ありますが|[0-9０-９]|歳以上|歳未満|期限|以内|以降|以前|限定|条件|限った|限り|要介護|障害|障がい|認定|居住|所得', value))


def display_record(record):
    result = dict(record)
    if unsupported_negative(record, 'what', record.get('what')):
        result.pop('what')
    if record.get('k') == 'notfound' and not has_sources(record):
        result['record_status'] = '独自の支援について、確認先の記録が不足しています。'
    return result
