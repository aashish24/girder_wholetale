add_python_test(basic PLUGIN wholetale)
add_python_test(harvester PLUGIN wholetale)
add_python_test(recipe PLUGIN wholetale)
add_python_test(image PLUGIN wholetale)
add_python_test(tale PLUGIN wholetale)
add_python_test(instance PLUGIN wholetale)
add_python_test(constants PLUGIN wholetale)
add_python_test(dataone_register PLUGIN wholetale)
add_python_test(dataone_upload PLUGIN wholetale)
add_python_test(dataone_utils PLUGIN wholetale)
add_python_test(dataone_package PLUGIN wholetale)
add_python_style_test(python_static_analysis_wholetale
                      "${PROJECT_SOURCE_DIR}/plugins/wholetale/server")
