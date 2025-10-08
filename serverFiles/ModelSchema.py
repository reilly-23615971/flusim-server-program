# Flusim Web Interface Application
# Developed by Reilly Evans
# Defines structure of model configuration guide JSON files

# Imports
import logging
from operator import attrgetter
from typing import Annotated, Literal, Optional, Any, cast
from annotated_types import Ge, Le
from typing_extensions import Self
from pydantic import (
    BaseModel, ValidationInfo,
    Field, model_validator, field_validator
)

# Logging
validationLog = logging.getLogger(__name__)

# Type Definitions
type AgeGroup = Literal[
    'young_infant', # 0-6 months
    'infant', # 7-24 months (0.5-2 years)
    'young_child', # 3-5 years
    'child', # 6-12 years
    'adolescent', # 13-17 years
    'young_adult', # 18-24 years
    'adult', # 25-44 years
    'older_adult', # 45-64 years
    'senior', # 65-79 years
    'older_senior' # 80+ years
]
type TriggerCondition = Literal[
    'none', 'timed', 'per_school_cases', 'community_cases',
    'community_rate', 'per_primary_high_school_cases'
]
type BoosterType = Literal['primary', 'booster']
type Kappa = Annotated[float, Ge(0)]
# The following 3 types are structurally identical, but are 
# distinguished for readability and documentation purposes
type Proportion = Annotated[float, Ge(0), Le(1)]
type Probability = Annotated[float, Ge(0), Le(1)]
type EfficacyValue = Annotated[float, Ge(0), Le(1)]

# Validation constants
parameterCategories = {
    'Scenario_CrossImmunity': ['FromStrainId', 'ToStrainId'], 
    'Scenario_SeededNaturalImmunity': ['StrainId', 'Age'], 
    'Scenario_Strain': ['StrainId'], 
    'Scenario_VaccineCoverage': ['Age'], 
    'Scenario_VaccineDose': ['DoseType'], 
    'Scenario_VaccineDoseEfficacy': ['DoseType', 'Age']
}
parameterGetters = {
    'Scenario_CrossImmunity': attrgetter('FromStrainId', 'ToStrainId'), 
    'Scenario_SeededNaturalImmunity': attrgetter('StrainId', 'Age'), 
    'Scenario_Strain': attrgetter('StrainId'), 
    'Scenario_VaccineCoverage': attrgetter('Age'), 
    'Scenario_VaccineDose': attrgetter('DoseType'), 
    'Scenario_VaccineDoseEfficacy': attrgetter('DoseType', 'Age')
}



# Parameter Models

# Set of scenario parameters set collectively for all age groups
class ageScenarioParameters(BaseModel):
    trans: Optional[float] = Field(
        title = 'Transmission', default = None, ge = 0.0, description = ((
            'The probability of transmission for all age groups will '
            'be multiplied by this value; the higher this is, the more '
            'likely it is that infected individuals will spread the '
            'disease to others.'
        ))
    )
    susc: Optional[float] = Field(
        title = 'Susceptibility', default = None, ge = 0.0, description = ((
            'The probability of transmission for all age groups will '
            'be multiplied by this value; the higher this is, the more '
            'likely it is that uninfected individuals will catch the '
            'disease from others.'
        ))
    )
    social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance', default = None, 
        description = ((
            'The probability of complying with social distancing '
            'procedures for all age groups.'
        ))
    )
    mort: Optional[Probability] = Field(
        title = 'Mortality', default = None, description = ((
            'The probability of dying from '
            'the disease for all age groups.'
        ))
    )

    class Config:
        validate_assignment = True

# Set of scenario parameters modifying the simulation
class scenarioParameters(BaseModel):
    # Seeding Parameters
    seed_rate: Optional[float] = Field(
        title = 'Seeding Rate', default = 0.125, ge = 0.0, description = ((
            'The average number of infections to '
            'introduce into the simulation per cycle.'
        ))
    )
    start_day_of_week: Optional[int] = Field(
        title = 'Starting Day of Week', default = 0, ge = 0, le = 6, 
        description = ((
            'The day of the week on cycle 0 of each simulation run as an '
            'integer. Zero-indexed such that Sunday is 0, Monday is 1, etc.'
        ))
    )
    seeding_duration: Optional[int] = Field(
        title = 'Seeding Duration', default = 720, ge = 0, description = (
            'The number of cycles that infection seeding will occur for.'
        )
    )
    seeding_start_cycle: Optional[int] = Field(
        title = 'Seeding Starting Cycle', default = 0, ge = 0, description = (
            'The first cycle in which infection seeding should occur.'
        )
    )

    # Transmission Parameters
    beta_asymptomatic: Optional[float] = Field(
        title = 'Beta (Asymptomatic)', default = 0.55, ge = 0.0, 
        description = ((
            'The probability of transmission from asymptomatic '
            'individuals will be multiplied by this value.'
        ))
    )
    beta_post_symptomatic: Optional[float] = Field(
        title = 'Beta (Post-Symptomatic)', default = 0.55, ge = 0.0, 
        description = ((
            'The probability of transmission from infected individuals whose '
            'symptomatic period has ended will be multiplied by this value.'
        ))
    )
    kappa_household: Optional[Kappa] = Field(
        title = 'Kappa (Household)', default = 2.2, description = ((
            'The probability of transmission between two individuals located '
            'in the same household will be multiplied by this value.'
        ))
    )
    kappa_child_education: Optional[Kappa] = Field(
        title = 'Kappa (Child Education)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same child education facility will be multiplied by '
            'this value.'
        ))
    )
    kappa_adult_education: Optional[Kappa] = Field(
        title = 'Kappa (Adult Education)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same adult education facility will be multiplied by '
            'this value.'
        ))
    )
    kappa_workplace: Optional[Kappa] = Field(
        title = 'Kappa (Workplace)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same workplace will be multiplied by this value.'
        ))
    )
    kappa_child_care: Optional[Kappa] = Field(
        title = 'Kappa (Childcare)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same childcare facility will be multiplied by this value.'
        ))
    )
    kappa_hospital: Optional[Kappa] = Field(
        title = 'Kappa (Hospital)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same hospital will be multiplied by this value.'
        ))
    )
    kappa_background: Optional[Kappa] = Field(
        title = 'Kappa (Background)', default = 1.0, description = ((
            'The probability of transmission between two individuals during '
            'the background phase of the simulation will be multiplied by '
            'this value.'
        ))
    )

    # Infection Parameters
    prob_asymptomatic: Optional[Probability] = Field(
        title = 'Adult Asymptomatic Probability', default = 0.35, 
        description = (
            'The probability of an infected adult being asymptomatic.'
        )
    )
    prob_asymptomatic_young: Optional[Probability] = Field(
        title = 'Child Asymptomatic Probability', default = 0.35, 
        description = (
            'The probability of an infected child being asymptomatic.'
        )
    )
    transmissibility_delay: Optional[int] = Field(
        title = 'Transmissibility Delay', default = 10, ge = 0, 
        description = ((
            'The length of the latent period, i.e. the number of cycles '
            'before an infected individual becomes infectious themselves.'
        ))
    )
    symptom_latency: Optional[int] = Field(
        title = 'Symptom Latency', default = 12, ge = 0, description = ((
            'The length of the incubation period, i.e. the number of cycles '
            'before an infected individual begins to show symptoms.'
        ))
    )
    generation_time: Optional[int] = Field(
        title = 'Generation Time', default = 19, ge = 0, description = ((
            'The number of cycles before an infected individual ceases to '
            'show symptoms. Subtracting the latent period from this value '
            'provides the infectious period.'
        ))
    )
    infection_duration: Optional[int] = Field(
        title = 'Infection Duration', default = 19, ge = 0, description = ((
            'The number of cycles before an infected '
            'individual is considered to have recovered.'
        ))
    )

    # Behaviour Parameters
    prob_withdrawal: Optional[Probability] = Field(
        title = 'Adult Withdrawal Probability', default = 0.5, description = ((
            'The probability of an infected adult withdrawing '
            'from work after becoming symptomatic.'
        ))
    )
    prob_school_withdrawal: Optional[Probability] = Field(
        title = 'Child Withdrawal Probability', default = 0.9, description = ((
            'The probability of an infected child withdrawing '
            'from school after becoming symptomatic.'
        ))
    )
    prob_hospitalisation: Optional[Probability] = Field(
        title = 'Hospitalisation Probability', default = 0.0, description = ((
            'The probability of an infected individual '
            'being hospitalised if they are diagnosed.'
        ))
    )
    prob_diagnosis: Optional[Probability] = Field(
        title = 'Diagnosis Probability', default = 0.5, description = ((
            'The probability of an infected individual being formally '
            'diagnosed as a case after becoming symptomatic.'
        ))
    )
    prob_child_supervision: Optional[Probability] = Field(
        title = 'Child Supervision Probability', default = 1.0, description = ((
            'The probability of an adult remaining in a household (regardless '
            'of where they would otherwise go) if a child is present at said '
            'household but no other adults are present.'
        ))
    )
    withdrawal_period: Optional[int] = Field(
        title = 'Adult Withdrawal Probability', default = 8, ge = 0, 
        description = ((
            'The number of cycles before an infected individual who is '
            'withdrawing from work/school will resume attending their '
            'work/school normally.'
        ))
    )

    # Health Outcome Parameters
    hospitalisation_rate: Optional[Probability] = Field(
        title = 'Hospitalisation Rate', default = 0.0, description = ((
            'The probability of hospitalisation occurring if an infected '
            'individual is symptomatic. Has been tagged as needing to be '
            'checked in the base schema; use prob_hospitalisation instead.'
        ))
    )

    # Contact Parameters
    background_contact_count: Optional[float] = Field(
        title = 'Background Contact Count', default = 4.0, ge = 0.0, 
        description = ((
            'The number of other individuals that are encountered by a single '
            'individual during the background phase of the simulation.'
        ))
    )
    max_class_size: Optional[int] = Field(
        title = 'Maximum Class Size', default = 10, ge = 0, description = ((
            'The maximum number of individuals that can be in a '
            'single class within a child education or childcare facility.'
        ))
    )
    max_adult_class_size: Optional[int] = Field(
        title = 'Maximum Adult Class Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can be '
            'in a single class within an adult education facility.'
        ))
    )
    max_workgroup_size: Optional[int] = Field(
        title = 'Maximum Workgroup Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can '
            'be in a single workgroup within a workplace.'
        ))
    )
    max_neighbourgroup_size: Optional[int] = Field(
        title = 'Maximum Neighbour Group Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can be '
            'in a single neighbour group within a neighbourhood.'
        ))
    )
    max_churchgroup_size: Optional[int] = Field(
        title = 'Maximum Church Group Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can '
            'be in a single church group within a church.'
        ))
    )
    max_class_count: Optional[int] = Field(
        title = 'Maximum Class Count', default = 1, ge = 0, description = ((
            'The maximum number of distinct classes that '
            'can exist within a single education facility.'
        ))
    )

    # Intervention Parameters
    diagnosis_delay: Optional[int] = Field(
        title = 'Diagnosis Delay', default = 1, ge = 0, description = ((
            'The number of cycles before a '
            'symptomatic individual can be diagnosed.'
        ))
    )
    case_trigger_threshold: Optional[int] = Field(
        title = 'Case Trigger Threshold', default = 1, ge = 0, description = ((
            'The minimum number of community cases that must be detected '
            'before an intervention with a case trigger will be triggered.'
        ))
    )
    rate_trigger_threshold: Optional[int] = Field(
        title = 'Rate Trigger Threshold', default = 1, ge = 0, description = ((
            'The minimum diagnosed cases per day that must be detected '
            'before an intervention with a rate trigger will be triggered.'
        ))
    )
    rate_relaxation_threshold: Optional[int] = Field(
        title = 'Rate Relaxation Threshold', default = 1, ge = 0, 
        description = ((
            'The maximum diagnosed cases per day that must be detected before '
            'an intervention with a rate relaxation trigger will be relaxed.'
        ))
    )
    maximum_trigger_count: Optional[int] = Field(
        title = 'Maximum Trigger Count', default = 250, ge = 0, description = ((
            'The maximum number of times an intervention '
            'can be triggered in a single simulation run.'
        ))
    )
    pandemic_alert: Optional[bool] = Field(
        title = 'Pandemic Alert', default = False, description = ((
            'If true, a pandemic alert will be active in the simulation, '
            'making groups social distance even if specific interventions '
            'are not active.'
        ))
    )

    # Isolation Parameters
    social_distance_compliance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance', default = 0.0, description = ((
            'The probability of an individual complying '
            'with social distancing procedures.'
        ))
    )
    diagnosed_case_isolation: Optional[bool] = Field(
        title = 'Diagnosed Case Isolation', default = False, description = ((
            'If true, infected individuals who have been formally diagnosed '
            'as a case will be isolated at their household in the simulation.'
        ))
    )
    class_dismissal: Optional[bool] = Field(
        title = 'Class Dismissal', default = False, description = ((
            'If true, classes at childcare and child education facilities '
            'will be dismissed when the daily diagnosed case rate exceeds '
            'rate_trigger_threshold.'
        ))
    )

    # Immunity Parameters
    infection_waning_cycle_delay: Optional[int] = Field(
        title = 'Infection Waning Cycle Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before an individual who has recovered from '
            'an infection will begin to lose their immunity to the disease.'
        ))
    )
    infection_waning_rate_per_cycle: Optional[float] = Field(
        title = 'Infection Waning Rate Per Cycle', default = 0.005, ge = 0.0, 
        description = ((
            'The proportion of immune individuals who will lose their '
            'immunity to the disease each cycle, once immunity waning '
            'has begun.'
        ))
    )
    infection_waned_protection: Optional[EfficacyValue] = Field(
        title = 'Infection Immunity After Waning', default = 0.5,
        description = ((
            'The efficacy of the immunity conferred from infection '
            'after it has waned to the maximum degree.'
        ))
    )

    # School Closure Parameters
    close_childcare: Optional[bool] = Field(
        title = 'Close Childcare', default = False, description = ((
            'If true, childcare facilities will be included in '
            'the set of facilities affected by school closure NPIs.'
        ))
    )
    close_child_education: Optional[bool] = Field(
        title = 'Close Child Education', default = True, description = ((
            'If true, child education facilities will be included in '
            'the set of facilities affected by school closure NPIs.'
        ))
    )
    close_adult_education: Optional[bool] = Field(
        title = 'Close Adult Education', default = False, description = ((
            'If true, adult education facilities will be included in '
            'the set of facilities affected by school closure NPIs.'
        ))
    )
    school_closure_compliance: Optional[float] = Field(
        title = 'School Closure Compliance', default = 0.5, ge = 0, le = 1, 
        description = ((
            'The proportion of individuals in a school '
            'who will comply with school closure NPIs.'
        ))
    )
    school_closure_trigger: Optional[TriggerCondition] = Field(
        title = 'School Closure Trigger', default = 'none', description = ((
            'The trigger condition that will enable school '
            'closure NPIs in the simulation when fulfilled.'
        ))
    )
    school_closure_relaxation: Optional[TriggerCondition] = Field(
        title = 'School Closure Relaxation Trigger', default = 'none', 
        description = ((
            'The trigger condition that will disable school '
            'closure NPIs in the simulation when fulfilled.'
        ))
    )
    school_closure_duration: Optional[int] = Field(
        title = 'School Closure Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a school closure NPI is '
            'automatically relaxed, when school_closure_trigger '
            'is set to "timed".'
        ))
    )
    school_closure_delay: Optional[int] = Field(
        title = 'School Closure Delay', default = 0, ge = 0, description = ((
            'The number of cycles before a school closure NPI comes '
            'into effect, when school_closure_trigger is set to "timed".'
        ))
    )

    # Withdrawal Increase Parameters
    withdrawal_increase_trigger: Optional[TriggerCondition] = Field(
        title = 'Withdrawal Increase Trigger', default = 'none', 
        description = ((
            'The trigger condition that will enable withdrawal increase NPIs '
            'in the simulation when fulfilled.'
        ))
    )
    withdrawal_increase_relaxation: Optional[TriggerCondition] = Field(
        title = 'Withdrawal Increase Relaxation Trigger', default = 'none', 
        description = ((
            'The trigger condition that will disable withdrawal increase NPIs '
            'in the simulation when fulfilled.'
        ))
    )
    withdrawal_increase_delay: Optional[int] = Field(
        title = 'Withdrawal Increase Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a withdrawal increase NPI comes into '
            'effect, when withdrawal_increase_trigger is set to "timed".'
        ))
    )
    withdrawal_increase_duration: Optional[int] = Field(
        title = 'Withdrawal Increase Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a withdrawal increase NPI is '
            'automatically relaxed, when withdrawal_increase_relaxation '
            'is set to "timed".'
        ))
    )
    increased_withdrawal: Optional[float] = Field(
        title = 'Increased Adult Withdrawal Probability', default = 0.9, 
        ge = 0.0, description = ((
            'The probability of an infected adult withdrawing from '
            'work after becoming symptomatic, when a withdrawal increase '
            'NPI is in effect.'
        ))
    )
    increased_withdrawal_child: Optional[float] = Field(
        title = 'Increased Child Withdrawal Probability', default = 0.9, 
        ge = 0.0, description = ((
            'The probability of an infected child withdrawing from '
            'school after becoming symptomatic, when a withdrawal increase '
            'NPI is in effect.'
        ))
    )

    # Reduced Workgroup Parameters
    reduced_workgroup_size: Optional[int] = Field(
        title = 'Reduced Workgroup Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can be in a single '
            'workgroup within a workplace, when a reduced workgroup '
            'NPI is in effect.'
        ))
    )
    reduced_workgroup_trigger: Optional[TriggerCondition] = Field(
        title = 'Reduced Workgroup Trigger', default = 'none', description = ((
            'The trigger condition that will enable reduced '
            'workgroup NPIs in the simulation when fulfilled.'
        ))
    )
    reduced_workgroup_relaxation: Optional[TriggerCondition] = Field(
        title = 'Reduced Workgroup Relaxation Trigger', default = 'none', 
        description = ((
            'The trigger condition that will disable reduced '
            'workgroup NPIs in the simulation when fulfilled.'
        ))
    )
    reduced_workgroup_delay: Optional[int] = Field(
        title = 'Reduced Workgroup Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a reduced workgroup NPI comes '
            'into effect, when reduced_workgroup_trigger is set to "timed".'
        ))
    )
    reduced_workgroup_duration: Optional[int] = Field(
        title = 'Reduced Workgroup Duration', default = 56, ge = 0, 
        description = ((
            'The number of cycles before a reduced workgroup NPI is '
            'automatically relaxed, when reduced_workgroup_relaxation '
            'is set to "timed".'
        ))
    )

    # Work Nonattendance Parameters
    prob_work_nonattendance: Optional[Probability] = Field(
        title = 'Work Nonattendance Probability', default = 0.5, 
        description = ((
            'The probability of an infected individual not going '
            'to work, when a work nonattendance NPI is in effect.'
        ))
    )
    work_nonattendance_trigger: Optional[TriggerCondition] = Field(
        title = 'Work Nonattendance Trigger', default = 'none', 
        description = ((
            'The trigger condition that will enable work '
            'nonattendance NPIs in the simulation when fulfilled.'
        ))
    )
    work_nonattendance_relaxation: Optional[TriggerCondition] = Field(
        title = 'Work Nonattendance Relaxation Trigger', default = 'none', 
        description = ((
            'The trigger condition that will disable work '
            'nonattendance NPIs in the simulation when fulfilled.'
        ))
    )
    work_nonattendance_delay: Optional[int] = Field(
        title = 'Work Nonattendance Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a work nonattendance NPI comes '
            'into effect, when work_nonattendance_trigger is set to "timed".'
        ))
    )
    work_nonattendance_duration: Optional[int] = Field(
        title = 'Work Nonattendance Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a work nonattendance NPI is '
            'automatically relaxed, when work_nonattendance_relaxation '
            'is set to "timed".'
        ))
    )

    # Background Contact Count Reduction Parameters
    bcc_reduction: Optional[float] = Field(
        title = 'Background Contact Count Reduction', default = 1.0, ge = 0.0, 
        description = ((
            'The multiplier applied to the number of contacts '
            'encountered per individual in the background phase, '
            'when BCC reduction NPIs are enabled in the simulation.'
        ))
    )
    bcc_reduction_trigger: Optional[TriggerCondition] = Field(
        title = 'BCC Reduction Trigger', default = 'none', description = ((
            'The trigger condition that will enable BCC '
            'reduction NPIs in the simulation when fulfilled.'
        ))
    )
    bcc_reduction_relaxation: Optional[TriggerCondition] = Field(
        title = 'BCC Reduction Relaxation Trigger', default = 'none', 
        description = ((
            'The trigger condition that will disable BCC '
            'reduction NPIs in the simulation when fulfilled.'
        ))
    )
    bcc_reduction_delay: Optional[int] = Field(
        title = 'BCC Reduction Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a BCC reduction NPI comes '
            'into effect, when bcc_reduction_trigger is set to "timed".'
        ))
    )
    bcc_reduction_duration: Optional[int] = Field(
        title = 'BCC Reduction Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a BCC reduction NPI is '
            'automatically relaxed, when bcc_reduction_relaxation '
            'is set to "timed".'
        ))
    )

    # Vaccination Parameters
    vaccination_priority: Optional[list[
        Literal['elderly', 'healthcare', 'essential_workers','other']
    ]] = Field(
        default = ['elderly', 'healthcare', 'essential_workers','other'], 
        title = 'Vaccination Priority', description = ((
            'A list of notable demographics in the population. Individuals '
            'who are part of demographics earlier on the list will receive '
            'vaccines before other individuals when there are not enough '
            'vaccines for everyone.'
        ))
    )
    vaccine_doses: Optional[int] = Field(
        title = 'Initial Vaccine Doses', default = 0, ge = 0, 
        description = ((
            'The number of vaccine doses available '
            'at the beginning of the simulation.'
        ))
    )
    vaccination_first_dose_rate: Optional[int] = Field(
        title = 'Vaccination First Dose Rate', default = 0, ge = 0, 
        description = ((
            'The daily rate at which individuals '
            'receive their first dose of the vaccine.'
        ))
    )
    vaccination_trigger: Optional[TriggerCondition] = Field(
        title = 'Vaccination Trigger', default = 'none', description = ((
            'The trigger condition that will enable '
            'vaccination in the simulation when fulfilled.'
        ))
    )
    vaccination_relaxation: Optional[TriggerCondition] = Field(
        title = 'Vaccination Relaxation Trigger', default = 'none', 
        description = ((
            'The trigger condition that will disable '
            'vaccination in the simulation when fulfilled.'
        ))
    )
    vaccination_delay: Optional[int] = Field(
        title = 'Vaccination Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a vaccination intervention comes '
            'into effect, when vaccination_trigger is set to "timed".'
        ))
    )
    vaccination_duration: Optional[int] = Field(
        title = 'Vaccination Duration', default = 56, ge = 0, 
        description = ((
            'The number of cycles before a vaccination intervention is '
            'automatically relaxed, when vaccination_relaxation '
            'is set to "timed".'
        ))
    )

    # Age-Specific Transmissibility
    young_infant_trans: Optional[float] = Field(
        title = 'Transmission (Young Infant)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is less than 6 '
            'months old. The higher this is, the more likely it is '
            'that infected young infants will spread the disease to '
            'others.'
        ))
    )
    infant_trans: Optional[float] = Field(
        title = 'Transmission (Infant)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 7-24 months '
            'old. The higher this is, the more likely it is that '
            'infected infants will spread the disease to others.'
        ))
    )
    young_child_trans: Optional[float] = Field(
        title = 'Transmission (Young Child)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 3-5 years old. '
            'The higher this is, the more likely it is that infected '
            'young children will spread the disease to others.'
        ))
    )
    child_trans: Optional[float] = Field(
        title = 'Transmission (Child)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 6-12 years '
            'old. The higher this is, the more likely it is that '
            'infected children will spread the disease to others.'
        ))
    )
    adolescent_trans: Optional[float] = Field(
        title = 'Transmission (Adolescent)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 13-17 years '
            'old. The higher this is, the more likely it is that '
            'infected adolescents will spread the disease to others.'
        ))
    )
    young_adult_trans: Optional[float] = Field(
        title = 'Transmission (Young Adult)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 18-24 years '
            'old. The higher this is, the more likely it is that '
            'infected young adults will spread the disease to others.'
        ))
    )
    adult_trans: Optional[float] = Field(
        title = 'Transmission (Adult)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 25-44 years '
            'old. The higher this is, the more likely it is that '
            'infected adults will spread the disease to others.'
        ))
    )
    older_adult_trans: Optional[float] = Field(
        title = 'Transmission (Older Adult)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 45-64 years '
            'old. The higher this is, the more likely it is that '
            'infected older adults will spread the disease to others.'
        ))
    )
    senior_trans: Optional[float] = Field(
        title = 'Transmission (Senior)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is 65-79 years '
            'old. The higher this is, the more likely it is that '
            'infected seniors will spread the disease to others.'
        ))
    )
    older_senior_trans: Optional[float] = Field(
        title = 'Transmission (Older Senior)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the infected individual is over 80 years '
            'old. The higher this is, the more likely it is that '
            'infected older seniors will spread the disease to others.'
        ))
    )

    # Age-Specific Susceptibility
    young_infant_susc: Optional[float] = Field(
        title = 'Susceptibility (Young Infant)', default = None, ge = 0, 
        description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is less than 6 '
            'months old. The higher this is, the more likely it is '
            'that uninfected young infants will catch the disease from '
            'others.'
        ))
    )
    infant_susc: Optional[float] = Field(
        title = 'Susceptibility (Infant)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 7-24 months '
            'old. The higher this is, the more likely it is that '
            'uninfected infants will catch the disease from others.'
        ))
    )
    young_child_susc: Optional[float] = Field(
        title = 'Susceptibility (Young Child)', default = None, ge = 0, 
        description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 3-5 years '
            'old. The higher this is, the more likely it is that '
            'uninfected young children will catch the disease from '
            'others.'
        ))
    )
    child_susc: Optional[float] = Field(
        title = 'Susceptibility (Child)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 6-12 years '
            'old. The higher this is, the more likely it is that '
            'uninfected children will catch the disease from others.'
        ))
    )
    adolescent_susc: Optional[float] = Field(
        title = 'Susceptibility (Adolescent)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 13-17 years '
            'old. The higher this is, the more likely it is that '
            'uninfected adolescents will catch the disease from others.'
        ))
    )
    young_adult_susc: Optional[float] = Field(
        title = 'Susceptibility (Young Adult)', default = None, ge = 0, 
        description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 18-24 years '
            'old. The higher this is, the more likely it is that '
            'uninfected young adults will catch the disease from '
            'others.'
        ))
    )
    adult_susc: Optional[float] = Field(
        title = 'Susceptibility (Adult)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 25-44 years '
            'old. The higher this is, the more likely it is that '
            'uninfected adults will catch the disease from others.'
        ))
    )
    older_adult_susc: Optional[float] = Field(
        title = 'Susceptibility (Older Adult)', default = None, ge = 0, 
        description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 45-64 years '
            'old. The higher this is, the more likely it is that '
            'uninfected older adults will catch the disease from '
            'others.'
        ))
    )
    senior_susc: Optional[float] = Field(
        title = 'Susceptibility (Senior)', default = None, ge = 0, description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is 65-79 years '
            'old. The higher this is, the more likely it is that '
            'uninfected seniors will catch the disease from others.'
        ))
    )
    older_senior_susc: Optional[float] = Field(
        title = 'Susceptibility (Older Senior)', default = None, ge = 0, 
        description = ((
            'The probability of transmission will be multiplied by '
            'this value when the uninfected individual is over 80 '
            'years old. The higher this is, the more likely it is that '
            'uninfected older seniors will catch the disease from '
            'others.'
        ))
    )

    # Age-Specific Social Distancing
    young_infant_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Young Infant)', 
        default = None, description = ((
            'The probability that an individual who is less than 6 '
            'months old will comply with social distancing procedures.'
        ))
    )
    infant_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Infant)', 
        default = None, description = ((
            'The probability that an individual who is 7-24 months old '
            'will comply with social distancing procedures.'
        ))
    )
    young_child_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Young Child)', 
        default = None, description = ((
            'The probability that an individual who is 3-5 years old '
            'will comply with social distancing procedures.'
        ))
    )
    child_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Child)', 
        default = None, description = ((
            'The probability that an individual who is 6-12 years old '
            'will comply with social distancing procedures.'
        ))
    )
    adolescent_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Adolescent)', 
        default = None, description = ((
            'The probability that an individual who is 13-17 years old '
            'will comply with social distancing procedures.'
        ))
    )
    young_adult_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Young Adult)', 
        default = None, description = ((
            'The probability that an individual who is 18-24 years old '
            'will comply with social distancing procedures.'
        ))
    )
    adult_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Adult)', 
        default = None, description = ((
            'The probability that an individual who is 25-44 years old '
            'will comply with social distancing procedures.'
        ))
    )
    older_adult_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Older Adult)', 
        default = None, description = ((
            'The probability that an individual who is 45-64 years old '
            'will comply with social distancing procedures.'
        ))
    )
    senior_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Senior)', 
        default = None, description = ((
            'The probability that an individual who is 65-79 years old '
            'will comply with social distancing procedures.'
        ))
    )
    older_senior_social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance (Older Senior)', 
        default = None, description = ((
            'The probability that an individual who is over 80 years '
            'old will comply with social distancing procedures.'
        ))
    )

    # Age-Specific Mortality
    young_infant_mort: Optional[Probability] = Field(
        title = 'Mortality (Young Infant)', default = None, description = ((
            'The probability that an individual who is less than 6 '
            'months old will die as a result of the disease.'
        ))
    )
    infant_mort: Optional[Probability] = Field(
        title = 'Mortality (Infant)', default = None, description = ((
            'The probability that an individual who is 7-24 months old '
            'will die as a result of the disease.'
        ))
    )
    young_child_mort: Optional[Probability] = Field(
        title = 'Mortality (Young Child)', default = None, description = ((
            'The probability that an individual who is 3-5 years old '
            'will die as a result of the disease.'
        ))
    )
    child_mort: Optional[Probability] = Field(
        title = 'Mortality (Child)', default = None, description = ((
            'The probability that an individual who is 6-12 years old '
            'will die as a result of the disease.'
        ))
    )
    adolescent_mort: Optional[Probability] = Field(
        title = 'Mortality (Adolescent)', default = None, description = ((
            'The probability that an individual who is 13-17 years old '
            'will die as a result of the disease.'
        ))
    )
    young_adult_mort: Optional[Probability] = Field(
        title = 'Mortality (Young Adult)', default = None, description = ((
            'The probability that an individual who is 18-24 years old '
            'will die as a result of the disease.'
        ))
    )
    adult_mort: Optional[Probability] = Field(
        title = 'Mortality (Adult)', default = None, description = ((
            'The probability that an individual who is 25-44 years old '
            'will die as a result of the disease.'
        ))
    )
    older_adult_mort: Optional[Probability] = Field(
        title = 'Mortality (Older Adult)', default = None, description = ((
            'The probability that an individual who is 45-64 years old '
            'will die as a result of the disease.'
        ))
    )
    senior_mort: Optional[Probability] = Field(
        title = 'Mortality (Senior)', default = None, description = ((
            'The probability that an individual who is 65-79 years old '
            'will die as a result of the disease.'
        ))
    )
    older_senior_mort: Optional[Probability] = Field(
        title = 'Mortality (Older Senior)', default = None, description = ((
            'The probability that an individual who is over 80 years '
            'old will die as a result of the disease.'
        ))
    )

    class Config:
        validate_assignment = True

# Key-value arguments passed directly to the simulator
class commandArgument(BaseModel):
    n_runs: Optional[int] = Field(
        title = 'Number of Runs', default = 24, ge = 15, description = ((
            'The number of simulation runs to perform. Simulations '
            'will not run correctly if the number of runs is less than 15.'
        ))
    )
    n_cycles: Optional[int] = Field(
        title = 'Number of Cycles', default = 720, ge = 1, description = ((
            'The number of simulation cycles to '
            'run before ending the simulation.'
        ))
    )

# Probability of recovering from multiple strains at once
class crossImmunity(BaseModel):
    FromStrainId: int = Field(
        title = 'Initial Strain ID', description = ((
            'The ID of the infection strain that '
            'an individual recovers from naturally.'
        ))
    )
    ToStrainId: int = Field(
        title = 'Additional Strain ID', description = ((
            'The ID of an infection strain that individuals may additionally '
            'recover from when recovering from the initial strain.'
        ))
    )
    ImmunityProportion: Optional[Proportion] = Field(
        title = 'Immunity Proportion', default = 1.0, description = ((
            'The proportion of individuals recovering from the initial strain '
            'who will also recover from the additional strain.'
        ))
    )

# Simulation parameters whose value will change at specific times
class dynamicIntervention(BaseModel):
    Name: Literal[
        'work_nonattendance', 'bcc_reduction', 'school_closure', 
        'seed_rate', 'school_closure_delay', 'school_closure_duration'
    ] = Field(
        title = 'Parameter Name', description = (
            'The parameter whose value will be updated.'
        )
    )
    CycleOffset: int = Field(
        title = 'Cycle Offset', description = (
            'The simulation cycle when the parameter will be updated.'
        )
    )
    NewValue: float = Field(
        title = 'New Value', description = ('The new value of the parameter.')
    )
    
# Seeding of naturally immune individuals into the population
class seededImmunity(BaseModel):
    StrainId: int = Field(
        title = 'Strain ID', description = ((
            'The ID of the infection strain that will have '
            'natural immunity seeded into the population.'
        ))
    )
    Age: Optional[AgeGroup] = Field(
        title = 'Age', default = None, description = ((
            'The age group which will have natural immunity seeded into it. '
            'If None, seeds immunity into all age groups.'
        ))
    )
    InitialProportion: Optional[Proportion] = Field(
        title = 'Initial Proportion', default = 0, description = ((
            'The proportion of the population which will have natural '
            'immunity to the infection at the beginning of each '
            'simulation run (cycle 0).'
        ))
    )
    ProportionPerCycle: Optional[Proportion] = Field(
        title = 'Proportion Per Cycle', default = 0, description = ((
            'The proportion of the population which will gain natural '
            'immunity to the infection at each cycle.'
        ))
    )
    TargetProportion: Optional[Proportion] = Field(
        title = 'Target Proportion', default = 0, description = ((
            'When this proportion of the population is immune to the '
            'infection, the simulation will stop seeding additional natural '
            'immunity into the population.'
        ))
    )

# Parameters for different strains to simulate in the same population
class strainParameters(BaseModel):
    StrainId: int = Field(
        title = 'Strain ID', description = (
            'The integer used to refer to this infection strain.'
        )
    )
    Beta: float = Field(
        title = 'Beta', description = (
            'The transmission coefficient for this infection strain.'
        )
    )
    SeedingWeight: Optional[float] = Field(
        title = 'Seeding Weight', default = 1, description = ((
            'The frequency at which this strain will be seeded into the '
            'population, proportional to other strains in the simulation'
        ))
    )

# Parameters for vaccine coverage across different age groups
class vaccineCoverage(BaseModel):
    Age: Optional[AgeGroup] = Field(
        title = 'Age', default = None, description = ((
            'The age group these parameters apply to. '
            'If None, the parameters apply to all age groups.'
        ))
    )
    Initial: Optional[Proportion] = Field(
        title = 'Initial Vaccinated Proportion', default = 0.0, 
        description = ((
            'The proportion of the population which will be vaccinated at the '
            'beginning of each simulation run (cycle 0).'
        ))
    )
    Target: EfficacyValue = Field(
        title = 'Target Vaccinated Proportion', description = ((
            'The proportion of the population which is being targeted for '
            'vaccination. If enough doses are available, this is the '
            'proportion of the population that will end up being vaccinated.'
        ))
    )

# Parameters for different vaccine dose types
class vaccineDose(BaseModel):
    DoseType: BoosterType = Field(
        title = 'Dose Type', description = (
            'The type of vaccine dose these parameters apply to.'
        )
    )
    Count: int = Field(
        title = 'Number of Doses', ge = 0, description = ((
            'The number of doses that will be administered to each individual '
            'for this type of vaccine dose.'
        ))
    )
    DoseSpacingCycles: int = Field(
        title = 'Dose Spacing Cycles', ge = 1, description = ((
            'The number of cycles before an individual who has '
            'received this vaccine dose can receive another one.'
        ))
    )
    WaningDelay: int = Field(
        title = 'Waning Delay', ge = 1, description = ((
            'The number of cycles before an individual who has received this '
            'vaccine dose will begin to lose their immunity to the disease.'
        ))
    )
    WaningRatePerCycle: Proportion = Field(
        title = 'Waning Rate per Cycle', description = ((
            'The proportion of vaccinated individuals who will lose their '
            'immunity to the disease each cycle, once immunity waning '
            'has begun.'
        ))
    )

# Parameters controlling efficacy of different vaccine doses
class vaccineEfficacy(BaseModel):
    DoseType: BoosterType = Field(
        title = 'Dose Type', description = (
            'The type of vaccine dose these parameters apply to.'
        )
    )
    Age: Optional[AgeGroup] = Field(
        title = 'Age', default = None, description = ((
            'The age group these parameters apply to. '
            'If None, the parameters apply to all age groups.'
        ))
    )
    Efficacy: EfficacyValue | list[EfficacyValue] = Field(
        title = 'Efficacy', description = (
            'The total population effectiveness of '
            'each primary dose / all booster doses.'
        )
    )
    WanedEfficacy: EfficacyValue = Field(
        title = 'Waned Efficacy', description = (
            'The total population effectiveness after all '
            'primary doses / each booster dose has waned.'
        )
    )



    # Efficacy should be list for primary and single value for booster
    @model_validator(mode = 'after')
    def efficacyValidation(self) -> Self:
        try:
            if self.DoseType == 'primary' and not isinstance(self.Efficacy, list):
                raise ValueError((
                    'The efficacy in Scenario_VaccineDoseEfficacy '
                    'should be a list when the dose type is "primary".'
                ))
            elif self.DoseType == 'booster' and isinstance(self.Efficacy, list):
                raise ValueError(
                    'The efficacy in Scenario_VaccineDoseEfficacy should '
                    'be a single value when the dose type is "booster".'
                )
            return self
        except ValueError as e:
            validationLog.error(
                f'[vaccineEfficacy] Encountered {type(e).__name__}: {e}'
            )
            raise e

# Class for compiling all parameter types into one object
class Parameters(BaseModel):
    Command_Argument: Optional[commandArgument] = Field(
        title = 'Command Arguments', default = None, description = (
            'Parameters passed to the simulation on the command line.'
        )
    )
    Scenario_ParameterWithAgePrefix: Optional[ageScenarioParameters] = Field(
        title = 'Age-Based Scenario Parameters', default = None, 
        description = ((
            'Parameters that will have unique values defined '
            'for each possible age category in the simulation.'
        ))
    )
    Scenario_Parameter: Optional[scenarioParameters] = Field(
        title = 'Scenario Parameters', default = None, description = ((
            'General model parameters that will populate the '
            'Scenario_Parameter table used by the simulation.'
        ))
    )
    # Note that the rest of the parameters are defined as lists of their
    # respective classes, not single objects
    Scenario_CrossImmunity: Optional[list[crossImmunity]] = Field(
        title = 'Cross Immunity Parameters', default = None, description = ((
            'Parameters controlling how an individual recovering from one '
            'infection strain can gain immunity to other infection strains.'
        ))
    )
    Scenario_DynamicIntervention: Optional[list[dynamicIntervention]] = Field(
        title = 'Dynamic Intervention Parameters', default = None, 
        description = ((
            'Parameters whose values will change '
            'at specific points in the simulation.'
        ))
    )
    Scenario_SeededNaturalImmunity: Optional[list[seededImmunity]] = Field(
        title = 'Seeded Natural Immunity Parameters', default = None, 
        description = ((
            'Parameters controlling how individuals naturally gain immunity '
            'to the disease without requiring infection or vaccination.'
        ))
    )
    Scenario_Strain: Optional[list[strainParameters]] = Field(
        title = 'Strain Parameters', default = None, description = ((
            'Parameters defining different strains of the '
            'infection to simulate in the same population.'
        ))
    )
    Scenario_VaccineCoverage: Optional[list[vaccineCoverage]] = Field(
        title = 'Vaccine Coverage Parameters', default = None, description = (
            'Parameters defining how much of the population receives vaccines.'
        )
    )
    Scenario_VaccineDose: Optional[list[vaccineDose]] = Field(
        title = 'Vaccine Dose Parameters', default = None, description = ((
            'Parameters defining how many doses of different vaccine types '
            'the population receives, and how often they are administered.'
        ))
    )
    Scenario_VaccineDoseEfficacy: Optional[list[vaccineEfficacy]] = Field(
        title = 'Vaccine Dose Efficacy Parameters', default = None, 
        description = (
            'Parameters defining the efficacy of different vaccine doses.'
        )
    )



    # Wrap solo entries in list-based parameters
    @field_validator(
        'Scenario_CrossImmunity', 'Scenario_DynamicIntervention', 
        'Scenario_SeededNaturalImmunity', 'Scenario_Strain', 
        'Scenario_VaccineCoverage', 'Scenario_VaccineDose', 
        'Scenario_VaccineDoseEfficacy', mode = 'before'
    )
    @classmethod
    def listify(cls, value: Any) -> Optional[list]:
        if value is not None and not isinstance(value, list): return [value]
        else: return value

    # Prevent duplicate entries in list-based parameters 
    # (e.g. 2 Scenario_Strain objects with the same StrainId)
    @field_validator(
        'Scenario_CrossImmunity', 'Scenario_SeededNaturalImmunity', 
        'Scenario_Strain', 'Scenario_VaccineCoverage', 'Scenario_VaccineDose', 
        'Scenario_VaccineDoseEfficacy', mode = 'after'
    )
    @classmethod
    def noDuplicateCategories(
        cls, value: Optional[list[Any]], info: ValidationInfo
    ) -> Optional[list[Any]]:
        try:
            if value is None or info.field_name is None: return value
            # Identify duplicates in relevant category properties
            relevantCategories = parameterGetters[info.field_name]
            configuredValues = [relevantCategories(item) for item in value]
            duplicateValues = [
                item for item in set(configuredValues) 
                if configuredValues.count(item) > 1
            ]
            if duplicateValues:
                # Replace any None values for age with 
                # 'All Ages' for clarity in error messages
                if (
                    info.field_name == 'Scenario_SeededNaturalImmunity' 
                    or info.field_name == 'Scenario_VaccineDoseEfficacy'
                ): clearValues = [
                    (first, 'All Ages' if second is None else second) 
                    for first, second in duplicateValues
                ]
                else: clearValues = [
                    ('All Ages' if item is None else item) 
                    for item in duplicateValues
                ]
                raise AssertionError((
                    'The Flusim configuration file defined multiple '
                    f'{info.field_name} objects with the same values for the '
                    f'{' and '.join(parameterCategories[info.field_name])} '
                    'attribute(s), making it ambiguous which values apply '
                    f'to the following categories: {', '.join(clearValues)}. '
                    f'Ensure each {info.field_name} object has unique '
                    'values for these attributes.'
                ))
            return value
        except AssertionError as e:
            validationLog.error(
                f'[vaccineEfficacy] Encountered {type(e).__name__}: {e}'
            )
            raise e
        
    class Config:
        validate_assignment = True
    
    # Ensure the right number of efficacies for primary vaccines are defined
    @model_validator(mode = 'after')
    def efficacyCount(self, info: ValidationInfo) -> Self:
        if self.Scenario_VaccineDose and self.Scenario_VaccineDoseEfficacy:
            primaryDose = next((
                item for item in self.Scenario_VaccineDose 
                if item.DoseType == 'primary'
            ), None)
            primaryEfficacy = (
                item for item in self.Scenario_VaccineDoseEfficacy
                if item.DoseType == 'primary'
            )
            if primaryDose and primaryEfficacy and any(
                len(cast(list[EfficacyValue], item.Efficacy)) != 
                primaryDose.Count for item in primaryEfficacy
            ):
                raise ValueError((
                    'The efficacy list in Scenario_VaccineDoseEfficacy '
                    'should have a number of elements equal to the '
                    'count defined in Scenario_VaccineDose when '
                    'the dose type is "primary".'
                ))
        return self



# JSON Config Models

# Model for parameters to modify in simulations on a specific community
class communityOverride(BaseModel):
    name: str = Field(
        title = 'Name', description = (
            'The name of the community these parameters apply to.'
        )
    )
    parameters: Parameters = Field(
        title = 'Parameters', description = (
            'Parameters to modify for this community.'
        )
    )

# Model for templates used by simulation sets to modify parameters
class overrideTemplate(BaseModel):
    name: str = Field(
        title = 'Name', description = (
            'The name of the template.'
        )
    )
    description: Optional[str] = Field(
        title = 'Description', default = None, description = (
            'A brief description of the parameters described by the template.'
        )
    )
    notes: Optional[str] = Field(
        title = 'Description', default = None, description = (
            'Additional information about the template.'
        )
    )
    parameters: Parameters = Field(
        title = 'Parameters', description = (
            'Parameters to modify for this template.'
        )
    )

# Model for defining parameters for override templates or simulations
class overrideParams(BaseModel): 
    parameters: Parameters = Field(
        title = 'Parameters', description = ('The parameters to apply.')
    )

# Model for individual simulations and their parameters
class simulation(BaseModel):
    name: str = Field(
        title = 'Name', description = ('The name of this simulation.')
    )
    apply_template: Optional[list[str]] = Field(
        title = 'Applied Templates', default = None, description = ((
            'A list of names of override templates whose '
            'parameter values will be used by this simulation.'
        ))
    )
    override_setting: Optional[overrideParams] = Field(
        title = 'Override Settings', default = None, description = (
            'Parameters that will be applied to this simulation alone.'
        )
    )

# Model for collections of simulations to run together
class simulationSet(BaseModel):
    name: str = Field(title = 'Name', description = ('The name of this set.'))
    version: int | float = Field(
        title = 'Version', description = ((
            'The set number that will be inserted into the names of the '
            'files generated by the simulations, after the middle joint.'
        ))
    )
    skip: Optional[bool] = Field(
        title = 'Skip', default = False, description = (
            'If true, the model will not run this set of simulations.'
        )
    )
    simulations: list[simulation] = Field(
        title = 'Simulations', description = (
            'A list of scenarios to run in this set.'
        )
    )

    # Wrap solo simulations in list
    @field_validator('simulations', mode = 'before')
    @classmethod
    def listify(cls, value: Any) -> Optional[list]:
        if value is not None and not isinstance(value, list): return [value]
        else: return value

# Model for the full configuration JSON file
class modelGuideFile(BaseModel):
    name: str = Field(
        title = 'Name', description = (
            'The name of the simulation guide file.'
        )
    )
    description: Optional[str] = Field(
        title = 'Description', default = None, description = (
            'A brief description of the simulations the guide file defines.'
        )
    )
    output_folder: str = Field(
        title = 'Output Folder', default = './results/', description = (
            'The folder where the scenario database files will be output.'
        )
    )
    middle_joint: Optional[str] = Field(
        title = 'Middle Joint', default = '-web-app', description = ((
            'A descriptive string that will be inserted into the names of the '
            'files generated by the simulations, between the community name '
            'and the version number.'
        ))
    )
    community_used: list[str] = Field(
        title = 'Communities Used', default = ['newcastle'], description = ((
            'The communities to repeat all scenarios across, corresponding '
            'with the names of the communities configured in '
            '"toolbox_config.json".'
        ))
    )
    shared_overrides: Optional[overrideParams] = Field(
        title = 'Shared Overrides', default = None, description = (
            'Parameters that will be applied to all scenarios in the file.'
        )
    )
    community_overrides: Optional[list[communityOverride]] = Field(
        title = 'Community Overrides', default = None, description = ((
            'Parameters that will only be applied to '
            'simulations using specific communities'
        ))
    )
    override_templates: Optional[list[overrideTemplate]] = Field(
        title = 'Override Templates', default = None, description = ((
            'Templates containing a set of parameters that '
            'can be applied selectively to different scenarios.'
        ))
    )
    simulation_sets: list[simulationSet] = Field(
        title = 'Simulation Sets', description = (
            'A list of sets containing scenarios to run together.'
        )
    )

    # Wrap solo overrides/simulation sets in list
    @field_validator(
        'community_overrides', 'override_templates', 
        'simulation_sets', mode = 'before'
    )
    @classmethod
    def listify(cls, value: Any) -> Optional[list]:
        if value is not None and not isinstance(value, list): return [value]
        else: return value