#!/bin/bash

# Gitコミットメッセージテンプレートの設定
git config commit.template .gitmessage

echo "✅ Gitコミットメッセージテンプレートを設定しました"
echo ""
echo "次回から 'git commit' を実行すると、テンプレートが表示されます"
echo ""
echo "クイックコミットの場合:"
echo "  git commit -m \"Add: your message\""
echo ""
echo "テンプレート使用の場合:"
echo "  git commit  # エディタが開きます"
