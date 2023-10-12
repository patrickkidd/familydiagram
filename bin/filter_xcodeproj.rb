#!/usr/bin/env ruby

require 'xcodeproj'

OS_NAME = ARGV[0]
TARGET_NAME = ARGV[1]
SOURCE_FILE = ARGV[2]
source_file = File.basename(SOURCE_FILE)


def find_ref target, fname
    target.source_build_phase.files.each do |pbx_build_file|
        if pbx_build_file.file_ref.real_path.to_s.include? fname
            return pbx_build_file.file_ref.real_path.to_s
        end
    end
    return nil
end


if OS_NAME == 'osx'
    fpath = "build/osx/#{TARGET_NAME}.xcodeproj"
    p "Opening #{fpath} to add sources"
    project = Xcodeproj::Project.open(fpath)
    project.targets.each do |target|
        p "Found target #{target.name} in #{fpath}"
        if target.name == TARGET_NAME
            ref = find_ref(target, source_file)
            if not ref.nil?
                puts "**** Found #{source_file} in target, exiting"
            else
                # fnames = []
                # ARGV.each_with_index do |key, value|
                #     if key > 1
                #         fnames.push(value)
                #         puts "found: #{value}"
                #     end
                # end
                p SOURCE_FILE
                file_ref = project.reference_for_path(SOURCE_FILE)
                puts "filter_xcodeproj.rb: #{source_file} not found in target. Adding: #{file_ref}"
                target.add_file_references([file_ref])
                project.mark_dirty!
                project.save
                break
            end
        end
    end
end
