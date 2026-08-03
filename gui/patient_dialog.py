"""
Wrapper module: re-export updated dialog classes from the new `gui.dialogs.patient_dialog` to avoid duplicate implementations
and ensure UI improvements are used everywhere. This keeps backwards compatibility for imports that use
`from gui.patient_dialog import EditPatientDialog`.
"""

from gui.dialogs.patient_dialog import EditPatientDialog, PatientDetailsDialog, AddPatientDialog

__all__ = ["EditPatientDialog", "PatientDetailsDialog", "AddPatientDialog"]