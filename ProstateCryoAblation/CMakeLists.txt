#-----------------------------------------------------------------------------
set(MODULE_NAME ProstateCryoAblation)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ProstateCryoAblationUtil/__init__.py
  ProstateCryoAblationUtil/steps/__init__.py
  ProstateCryoAblationUtil/steps/intraOperativeTargeting.py
  ProstateCryoAblationUtil/appConfig.py
  ProstateCryoAblationUtil/UserEvents.py
  )

set(MODULE_PYTHON_RESOURCES
  #Resources/zframe/zframe-model.vtk
  #Resources/zframe/zframe-config.csv
  #Resources/zframe/ProstateTemplate.csv
  Resources/default.cfg
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
