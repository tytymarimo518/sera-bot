#!/usr/bin/env python3
"""
せらボット - cabinattendant.blog をもとにした個人チャットボット

使い方:
    python main.py          # チャット開始
    python main.py --update # 記事を更新してからチャット開始
    python main.py --update-only # 記事更新のみ（チャットなし）
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="せらボット")
    parser.add_argument("--update", action="store_true", help="起動前にブログを取得・更新する")
    parser.add_argument("--update-only", action="store_true", help="ブログ更新のみ行う（チャットなし）")
    args = parser.parse_args()

    if args.update or args.update_only:
        print("ブログ記事を取得中...")
        from scraper import run_update
        added = run_update()
        print(f"完了: {added} 件の新着記事を追加しました。")
        if args.update_only:
            return

    print()
    print("=" * 50)
    print("  せらボット へようこそ！")
    print("  元CAの投資家・せらとチャットできます。")
    print("  終了: 'exit' または Ctrl+C")
    print("  リセット: 'reset'")
    print("  記事再読み込み: 'reload'")
    print("=" * 50)
    print()

    try:
        from bot import SeraBot
        sera = SeraBot()
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

    print("せら: こんにちは！元CAのせらです。投資のこと、CAのこと、なんでも聞いてね！\n")

    while True:
        try:
            user_input = input("あなた: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nせら: またね！お金の勉強、一緒に続けよう！")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("せら: またね！お金の勉強、一緒に続けよう！")
            break
        if user_input.lower() == "reset":
            sera.reset()
            print("せら: 会話をリセットしたよ！また最初から話そう！\n")
            continue
        if user_input.lower() == "reload":
            sera.reload()
            print("せら: 最新記事を読み込んだよ！\n")
            continue

        try:
            response = sera.chat(user_input)
            print(f"\nせら: {response}\n")
        except Exception as e:
            print(f"エラーが発生しました: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
