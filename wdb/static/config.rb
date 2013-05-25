http_path = "/__wdb/"
css_dir = "stylesheets"
sass_dir = "sass"
images_dir = "images"
fonts_dir = "fonts"
javascripts_dir = "javascripts"

if environment == :production
  output_style = :compressed
else
  sass_options = { :debug_info => true }
  output_style = :expanded
end
