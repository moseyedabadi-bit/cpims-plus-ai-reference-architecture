#!/usr/bin/env ruby
# frozen_string_literal: true

require 'yaml'
require 'optparse'

options = { primero: nil, generated: nil }
OptionParser.new do |parser|
  parser.banner = 'Usage: qa_locale.rb --primero PATH --generated OUTPUT_DIR'
  parser.on('--primero PATH') { |v| options[:primero] = v }
  parser.on('--generated PATH') { |v| options[:generated] = v }
end.parse!
abort 'Missing --primero' unless options[:primero]
abort 'Missing --generated' unless options[:generated]

def flatten(value, prefix = nil, output = {})
  case value
  when Hash
    value.each do |key, child|
      path = [prefix, key].compact.join('.')
      flatten(child, path, output)
    end
  when Array
    value.each_with_index { |child, index| flatten(child, "#{prefix}[#{index}]", output) }
  else
    output[prefix] = value
  end
  output
end

upstream = YAML.safe_load(File.read(File.join(options[:primero], 'config/locales/fa-AF.yml'), encoding: 'UTF-8'), aliases: true).fetch('fa-AF')
generated = YAML.safe_load(File.read(File.join(options[:generated], 'config/locales/fa-IR.yml'), encoding: 'UTF-8'), aliases: true).fetch('fa-IR')

source_keys = flatten(upstream).keys.sort
target = flatten(generated)
target_keys = target.keys.sort
missing = source_keys - target_keys
extra = target_keys - source_keys

suspect_terms = %w[بلی نخیر فورم دوسیه قضیه پلان رهنما رجعت تغیر تاییدی]
suspects = target.select { |_key, value| value.is_a?(String) && suspect_terms.any? { |term| value.include?(term) } }

puts "source leaf keys: #{source_keys.length}"
puts "target leaf keys: #{target_keys.length}"
puts "missing keys: #{missing.length}"
puts "extra keys: #{extra.length}"
puts "suspect Dari/Iranian-Persian review strings: #{suspects.length}"

unless missing.empty?
  warn 'Missing keys:'
  missing.first(100).each { |key| warn "  #{key}" }
end
unless extra.empty?
  warn 'Extra keys:'
  extra.first(100).each { |key| warn "  #{key}" }
end
unless suspects.empty?
  warn 'Terminology review candidates:'
  suspects.first(100).each { |key, value| warn "  #{key}: #{value}" }
end

exit(missing.empty? ? 0 : 2)
