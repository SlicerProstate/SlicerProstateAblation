#-----------------------------------------------------------------------------
set(MODULE_NAME ProstateCryoAblation)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ProstateCryoAblationUtils/__init__.py
  ProstateCryoAblationUtils/steps/__init__.py
  ProstateCryoAblationUtils/steps/intraOperativeTargeting.py
  ProstateCryoAblationUtils/appConfig.py
  ProstateCryoAblationUtils/UserEvents.py
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
