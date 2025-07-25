#!/usr/bin/env bash

Describe 'extract-javadoc.sh single javadoc scenario'

  BeforeEach 'setup_test_dir'
  AfterEach 'cleanup_test_dir'

  setup_test_dir() {
    original_dir=$(pwd)

    # Create a directory that matches the pattern from the workflow: repo.XXXXXXXX
    # Use mktemp to get a temp name, then create it in current dir
    temp_name=$(mktemp -u repo.XXXXXXXX)
    test_dir="$original_dir/$temp_name"
    mkdir -p "$test_dir"
  }

  cleanup_test_dir() {
    cd "$original_dir" || return
    rm -rf "$test_dir"
  }

  # Helper function to create javadoc jar files
  create_javadoc_jar() {
    local jar_name="$1"
    local content_prefix="$2"

    echo "${content_prefix} javadoc content" > index.html
    echo "${content_prefix} package info" > package-summary.html
    zip -q "$jar_name" index.html package-summary.html
    rm index.html package-summary.html
  }

  Describe 'single javadoc file extraction'
    It 'should rename single javadoc file to javadoc.zip and extract to versioned directory'
      cd "$test_dir" || return

      create_javadoc_jar "sonar-plugin-api-13.0.0.3026-javadoc.jar" "dummy"

       When call "$original_dir/scripts/extract-javadoc.sh" "$test_dir" "13.0.0.3026"

      The status should be success
      The stdout should include "Found single javadoc file, using simple extraction"

      The file "javadoc.zip" should be exist

      The directory "javadoc/13.0.0.3026" should be exist
    End

    It 'should select main javadoc when test/fixture variants exist'
      cd "$test_dir" || return

      create_javadoc_jar "sonar-plugin-api-13.0.0.3026-javadoc.jar" "main"

      create_javadoc_jar "sonar-plugin-api-test-fixtures-13.0.0.3026-javadoc.jar" "test"

      When call "$original_dir/scripts/extract-javadoc.sh" "$test_dir" "13.0.0.3026"

      The status should be success
      The stdout should include "Found multiple javadoc files, selecting main one"
      The stdout should include "Selected main javadoc: sonar-plugin-api-13.0.0.3026-javadoc.jar"

      The file "javadoc.zip" should be exist

      The directory "javadoc/13.0.0.3026" should be exist
    End
  End
End
