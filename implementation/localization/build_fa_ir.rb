#!/usr/bin/env ruby
# frozen_string_literal: true

require 'yaml'
require 'digest'
require 'fileutils'
require 'optparse'

UPSTREAM = {
  'config/locales/fa-AF.yml' => 'c309697977d3b6ee0cf4ca1e2a5f8422526aa9cf',
  'config/locales/dates/fa-AF.yml' => '878619120a080fd9be6b57497744403020ab14b8'
}.freeze

REPLACEMENTS = {
  'بلی' => 'بله',
  'نخیر' => 'خیر',
  'فورم' => 'فرم',
  'فورم ها' => 'فرم‌ها',
  'دوسیه' => 'پرونده',
  'دوسیه ها' => 'پرونده‌ها',
  'قضیه' => 'پرونده',
  'قضایا' => 'پرونده‌ها',
  'پلان' => 'برنامه',
  'رهنما' => 'راهنما',
  'تغیر' => 'تغییر',
  'تغیرات' => 'تغییرات',
  'کود' => 'کد',
  'رجعت' => 'ارجاع',
  'تاییدی' => 'تأیید',
  'تایید' => 'تأیید',
  'مسترد شده' => 'رد شده',
  'فعلا' => 'فعلاً',
  'یاداشت' => 'یادداشت',
  'تبلیت' => 'تبلت',
  'میباشد' => 'است',
  'میباشند' => 'هستند'
}.freeze

MONTHS_IR = [nil, 'ژانویه', 'فوریه', 'مارس', 'آوریل', 'مه', 'ژوئن', 'ژوئیه', 'اوت', 'سپتامبر', 'اکتبر', 'نوامبر', 'دسامبر'].freeze

options = { upstream: nil, output: nil }
OptionParser.new do |parser|
  parser.banner = 'Usage: build_fa_ir.rb --upstream PATH_TO_PRIMERO --output OUTPUT_DIR'
  parser.on('--upstream PATH', 'Pinned Primero v2.14.5 checkout') { |v| options[:upstream] = v }
  parser.on('--output PATH', 'Output directory') { |v| options[:output] = v }
end.parse!

abort 'Missing --upstream' unless options[:upstream]
abort 'Missing --output' unless options[:output]

def git_blob_sha(content)
  Digest::SHA1.hexdigest("blob #{content.bytesize}\0#{content}")
end

def normalize_string(value)
  REPLACEMENTS.reduce(value.dup) { |text, (from, to)| text.gsub(from, to) }
end

def normalize(value)
  case value
  when Hash
    value.transform_values { |v| normalize(v) }
  when Array
    value.map { |v| normalize(v) }
  when String
    normalize_string(value)
  else
    value
  end
end

upstream_root = File.expand_path(options[:upstream])
output_root = File.expand_path(options[:output])
FileUtils.mkdir_p(File.join(output_root, 'config/locales/dates'))

UPSTREAM.each do |relative, expected_sha|
  path = File.join(upstream_root, relative)
  abort "Missing upstream file: #{relative}" unless File.file?(path)
  content = File.binread(path)
  actual_sha = git_blob_sha(content)
  abort "Upstream drift for #{relative}: expected #{expected_sha}, got #{actual_sha}" unless actual_sha == expected_sha
end

source = YAML.safe_load(File.read(File.join(upstream_root, 'config/locales/fa-AF.yml'), encoding: 'UTF-8'), aliases: true)
fa_af = source.fetch('fa-AF')
fa_ir = normalize(fa_af)

File.write(
  File.join(output_root, 'config/locales/fa-IR.yml'),
  { 'fa-IR' => fa_ir }.to_yaml(line_width: -1),
  mode: 'w', encoding: 'UTF-8'
)

dates_source = YAML.safe_load(File.read(File.join(upstream_root, 'config/locales/dates/fa-AF.yml'), encoding: 'UTF-8'), aliases: true)
dates = normalize(dates_source.fetch('fa-AF'))
dates['date'] ||= {}
dates['date']['month_names'] = MONTHS_IR
dates['date']['abbr_month_names'] = MONTHS_IR
dates['date']['today'] = 'امروز'
dates['date']['clear'] = 'پاک کردن'
dates['true'] = 'بله'
dates['false'] = 'خیر'

File.write(
  File.join(output_root, 'config/locales/dates/fa-IR.yml'),
  { 'fa-IR' => dates }.to_yaml(line_width: -1),
  mode: 'w', encoding: 'UTF-8'
)

puts "Generated fa-IR locale in #{output_root}"
