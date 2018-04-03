#-----------------------------------------------------------------------------
set(MODULE_NAME ProstateAblation)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ProstateAblationUtils/__init__.py
  ProstateAblationUtils/steps/__init__.py
  ProstateAblationUtils/steps/intraOperativeTargeting.py
  ProstateAblationUtils/appConfig.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/default.cfg
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
