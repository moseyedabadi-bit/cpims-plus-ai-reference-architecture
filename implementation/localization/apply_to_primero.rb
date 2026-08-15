#!/usr/bin/env ruby
# frozen_string_literal: true

require 'fileutils'
require 'optparse'

options = { primero: nil, generated: nil }
OptionParser.new do |parser|
  parser.banner = 'Usage: apply_to_primero.rb --primero PATH --generated OUTPUT_DIR'
  parser.on('--primero PATH', 'Primero v2.14.5 checkout') { |v| options[:primero] = v }
  parser.on('--generated PATH', 'Generated fa-IR directory') { |v| options[:generated] = v }
end.parse!

abort 'Missing --primero' unless options[:primero]
abort 'Missing --generated' unless options[:generated]

root = File.expand_path(options[:primero])
generated = File.expand_path(options[:generated])

files = {
  File.join(generated, 'config/locales/fa-IR.yml') => File.join(root, 'config/locales/fa-IR.yml'),
  File.join(generated, 'config/locales/dates/fa-IR.yml') => File.join(root, 'config/locales/dates/fa-IR.yml')
}
files.each do |src, dst|
  abort "Missing generated file #{src}" unless File.file?(src)
  FileUtils.mkdir_p(File.dirname(dst))
  FileUtils.cp(src, dst)
end

locale_rb = File.join(root, 'config/initializers/locale.rb')
text = File.read(locale_rb, encoding: 'UTF-8')
unless text.include?('fa-AF')
  abort 'Expected fa-AF locale anchor not found in locale.rb'
end
text = text.sub('es-GT fa-AF fr', 'es-GT fa-AF fa-IR fr') unless text.include?('fa-AF fa-IR')
text = text.sub('ar-SD fa-AF ku', 'ar-SD fa-AF fa-IR ku') unless text.include?('fa-AF fa-IR ku')
File.write(locale_rb, text, encoding: 'UTF-8')

fallbacks = File.join(root, 'config/initializers/locales_fallbacks.rb')
text = File.read(fallbacks, encoding: 'UTF-8')
unless text.include?("'fa-AF': EN_FALLBACK")
  abort 'Expected fa-AF fallback anchor not found'
end
unless text.include?("'fa-IR':")
  text = text.sub("  'fa-AF': EN_FALLBACK,", "  'fa-AF': EN_FALLBACK,\n  'fa-IR': %i[fa-AF en],")
end
File.write(fallbacks, text, encoding: 'UTF-8')

utils = File.join(root, 'app/javascript/components/i18n/utils.js')
text = File.read(utils, encoding: 'UTF-8')
unless text.include?('case "fa-AF":')
  abort 'Expected fa-AF RTL anchor not found in i18n utils'
end
unless text.include?('case "fa-IR":')
  text = text.sub('    case "fa-AF":', "    case \"fa-AF\":\n    case \"fa-IR\":")
end
File.write(utils, text, encoding: 'UTF-8')

puts 'Applied fa-IR locale and RTL/fallback support to Primero checkout.'
puts 'Review the resulting diff before build/deployment.'
