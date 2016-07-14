#!/usr/bin/env bash
# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

echogood() { echo "[1;32m *[0m $@"; }
echowarn() { echo "[1;33m *[0m $@"; }
echobad()  { echo "[1;31m *[0m $@"; }

echogood "Running unit tests ..."
if ! python -m unittest; then
  echobad "Unit test(s) failed; write minimal code to fix."
  exit 1
fi

echogood "All unit tests succeeded! Press enter to continue on to"
echogood "functional tests or type \`no\` to skip those and move on to"
echogood "refactoring."

echo -n "[33m>>>[0m "
read input

if [ -n "$input" ]; then
  case "${input:0:1}" in
    [Nn])
      echogood "Alright; refactor away!"
      exit 0
      ;;

    [Yy])
      ;;

    *)
      echobad "I dunno what you mean by \`$input\`"
      exit 1
      ;;
  esac
fi

echogood "Running functional tests ..."
if ! python functional_tests.py; then
  echobad "Functional tests failed; write a unit test."
  exit 1
fi

echogood "All tests succeeded! Either write a new functional test or"
echogood "start refactoring."
