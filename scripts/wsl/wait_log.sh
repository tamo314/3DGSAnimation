#!/bin/bash
# ログに指定の文字列が出るか、最大9分たつまで待ち、最後の進捗行を表示する。 使い方: wait_log.sh <ログ> <文字列>
for i in $(seq 1 54); do
  if grep -q "$2" "$1"; then echo FOUND; break; fi
  sleep 10
done
tr '\r' '\n' < "$1" | grep -E "^it |EVAL|Error" | tail -3 | cut -c1-200
