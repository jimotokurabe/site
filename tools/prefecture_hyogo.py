"""兵庫県の生成入口。共通の県ページ生成処理を利用する。"""
from prefecture_navigation import render_prefecture

def render_hyogo(out, draft=False):
    render_prefecture('hyogo',out,draft=draft)
