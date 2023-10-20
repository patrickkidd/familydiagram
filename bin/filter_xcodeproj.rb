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


class Options
    attr_accessor :path, :target, :method
  
    def initialize(args)
      @path = args[:path] || Dir.glob("*.xcodeproj").first
      @target = args[:target]
      @method = args[:method]
    end
  end
  
  def parse_args
    options_hash = {}
    args = ARGV
    args.each_with_index do |arg, index|
      case arg
      when '--project_path', '-p'
        path = args[index + 1]
        unless File.exist?(path)
          abort('There is no file at specified path.')
        end
        options_hash[:path] = path
      when '--target', '-t'
        options_hash[:target] = args[index + 1]
      when '--signing_method', '-m'
        method = args[index + 1]
        unless ['Automatic', 'Manual'].include?(method)
          abort("'Invalid signing method specified. Please use either 'Automatic' or 'Manual'")
        end
        options_hash[:method] = method
      end
    end
  
    options_hash
  end

if OS_NAME == 'osx'
    fpath = "build/osx/#{TARGET_NAME}.xcodeproj"
    p "Opening #{fpath} to add sources"
    project = Xcodeproj::Project.open(fpath)
    project.targets.each do |target|
        p "Found target #{target.name} in #{fpath}"
        if target.name == TARGET_NAME

            # Enable sources that should have been enabled
            ref = find_ref(target, source_file)
            if not ref.nil?
                puts "**** Found #{source_file} in target, skipping"
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
            end


            # # Force manual code signing (i.e. disable automatic in GUI)
            # # https://gist.github.com/thelvis4/253a2cdea8360da519b2a025c5d8fbac
            # target_id = target.uuid
            # attributes = project.root_object.attributes['TargetAttributes']
            # target_attributes = attributes[target_id]
            # target_attributes['ProvisioningStyle'] = options.method

            project.save
        end
    end
end
