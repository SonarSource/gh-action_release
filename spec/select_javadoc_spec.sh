#!/usr/bin/env bash

Describe 'select-javadoc.sh'

  BeforeEach 'setup_test_dirs'
  AfterEach 'cleanup_test_dirs'

  setup_test_dirs() {
    original_dir=$(pwd)
    test_dir="$original_dir/$(mktemp -u select-javadoc.XXXXXXXX)"
    public_dir="$test_dir/public"
    private_dir="$test_dir/private"
    dest_dir="$test_dir/dest"
    mkdir -p "$public_dir" "$private_dir" "$dest_dir"
  }

  cleanup_test_dirs() {
    cd "$original_dir" || return
    rm -rf "$test_dir"
  }

  select_javadoc() {
    export GITHUB_OUTPUT="$test_dir/github_output"
    : > "$GITHUB_OUTPUT"
    "$original_dir/scripts/select-javadoc.sh" "$public_dir" "$private_dir" "$dest_dir" "$1"
  }

  It 'copies only the public jar when the private dir is empty, regardless of publicRelease'
    touch "$public_dir/public-1.0-javadoc.jar"

    When call select_javadoc "false"

    The status should be success
    The file "$dest_dir/public-1.0-javadoc.jar" should be exist
    The file "$dest_dir/private-1.0-javadoc.jar" should not be exist
    The stdout should include "Found 1 public and 0 private javadoc jar(s)"
    The contents of file "$GITHUB_OUTPUT" should include "mixed=false"
  End

  It 'copies only the private jar when the public dir is empty, regardless of publicRelease'
    touch "$private_dir/private-1.0-javadoc.jar"

    When call select_javadoc "false"

    The status should be success
    The file "$dest_dir/private-1.0-javadoc.jar" should be exist
    The file "$dest_dir/public-1.0-javadoc.jar" should not be exist
    The stdout should include "Found 0 public and 1 private javadoc jar(s)"
    The contents of file "$GITHUB_OUTPUT" should include "mixed=false"
  End

  It 'copies only the public jar when both exist and publicRelease is false'
    touch "$public_dir/public-1.0-javadoc.jar"
    touch "$private_dir/private-1.0-javadoc.jar"

    When call select_javadoc "false"

    The status should be success
    The file "$dest_dir/public-1.0-javadoc.jar" should be exist
    The file "$dest_dir/private-1.0-javadoc.jar" should not be exist
    The stdout should include "Skipping 1 com.sonarsource.* javadoc jar(s)"
    The contents of file "$GITHUB_OUTPUT" should include "mixed=false"
  End

  It 'copies both jars and reports mixed=true when both exist and publicRelease is true'
    touch "$public_dir/public-1.0-javadoc.jar"
    touch "$private_dir/private-1.0-javadoc.jar"

    When call select_javadoc "true"

    The status should be success
    The file "$dest_dir/public-1.0-javadoc.jar" should be exist
    The file "$dest_dir/private-1.0-javadoc.jar" should be exist
    The stdout should include "Found 1 public and 1 private javadoc jar(s)"
    The contents of file "$GITHUB_OUTPUT" should include "mixed=true"
  End

  It 'copies nothing, without failing, when both are empty'
    When call select_javadoc "false"

    The status should be success
    The file "$dest_dir/public-1.0-javadoc.jar" should not be exist
    The file "$dest_dir/private-1.0-javadoc.jar" should not be exist
    The stdout should include "Found 0 public and 0 private javadoc jar(s)"
    The contents of file "$GITHUB_OUTPUT" should include "mixed=false"
  End
End
