# Flusim Web Interface Application
# Developed by Reilly Evans
# Defines structure of model configuration guide JSON files

# Imports
from operator import attrgetter
from typing import Annotated, Literal, Optional, Any, cast
from annotated_types import Ge, Le
from typing_extensions import Self
from pydantic import (
    BaseModel, ValidationError, ValidationInfo,
    Field, model_validator, field_validator, 
    InstanceOf
)

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
    'Scenario_CrossImmunity': ('FromStrainId', 'ToStrainId'), 
    'Scenario_SeededNaturalImmunity': ('StrainId', 'Age'), 
    'Scenario_Strain': ('StrainId'), 
    'Scenario_VaccineCoverage': ('Age'), 
    'Scenario_VaccineDose': ('DoseType'), 
    'Scenario_VaccineDoseEfficacy': ('DoseType', 'Age')
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
        title = 'Maximum Trigger Count', default = 10, ge = 0, description = ((
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
            'The number of other individuals that are encountered by a single '
            'individual during the background phase of the simulation will '
            'be multiplied by this value when a BCC reduction NPI '
            'is in effect.'
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

# Set of scenario parameters set individually for a specific age group
class ageScenarioParameters(BaseModel):
    trans: Optional[Probability] = Field(
        title = 'Transmission', default = None, description = ((
            'The transmissibility for individuals in the '
            'specified age group, overriding other parameters.'
        ))
    )
    susc: Optional[Probability] = Field(
        title = 'Susceptibility', default = None, description = ((
            'The susceptibility for individuals in the '
            'specified age group, overriding other parameters.'
        ))
    )
    social_distance: Optional[Probability] = Field(
        title = 'Social Distancing Compliance', default = None, 
        description = ((
            'The probability of complying with social distancing '
            'procedures for individuals in the specified age '
            'group, overriding other parameters.'
        ))
    )
    mort: Optional[Probability] = Field(
        title = 'Transmission', default = None, description = ((
            'The mortality for individuals in the specified '
            'age group, overriding other parameters.'
        ))
    )

# Key-value arguments passed directly to the simulator
class commandArgument(BaseModel):
    n_runs: Optional[int] = Field(
        title = 'Number of Runs', default = 24, ge = 1, description = (
            'The number of simulation runs to perform.'
        )
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
        'seed_rate', 'school_closure_delay' 'school_closure_duration'
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
        title = 'Target Vaccinated Efficacy', description = ((
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
        if self.DoseType == 'primary' and not isinstance(self.Efficacy, list):
            raise ValidationError((
                'The efficacy in Scenario_VaccineDoseEfficacy '
                'should be a list when the dose type is "primary".'
            ))
        elif self.DoseType == 'booster' and isinstance(self.Efficacy, list):
            raise ValidationError(
                'The efficacy in Scenario_VaccineDoseEfficacy should '
                'be a single value when the dose type is "booster".'
            )
        return self

# Class for compiling all parameter types into one object
class Parameters(BaseModel):
    Command_Argument: Optional[commandArgument] = Field(
        title = 'Command Arguments', default = None, description = (
            'Parameters passed to the simulation on the command line.'
        )
    )
    Scenario_Parameter: Optional[scenarioParameters] = Field(
        title = 'Scenario Parameters', default = None, description = ((
            'General model parameters that will populate the '
            'Scenario_Parameter table used by the simulation.'
        ))
    )
    Scenario_ParameterWithAgePrefix: Optional[ageScenarioParameters] = Field(
        title = 'Age-Based Scenario Parameters', default = None, 
        description = ((
            'Parameters that will have unique values defined '
            'for each possible age category in the simulation.'
        ))
    )
    # Note that the rest of the parameters are defined as lists of their
    # respective classes, not single objects
    Scenario_CrossImmunity: Optional[
        list[InstanceOf[crossImmunity]]
    ] = Field(
        title = 'Cross Immunity Parameters', default = None, description = ((
            'Parameters controlling how an individual recovering from one '
            'infection strain can gain immunity to other infection strains.'
        ))
    )
    Scenario_DynamicIntervention: Optional[
        list[InstanceOf[dynamicIntervention]]
    ] = Field(
        title = 'Dynamic Intervention Parameters', default = None, 
        description = ((
            'Parameters whose values will change '
            'at specific points in the simulation.'
        ))
    )
    Scenario_SeededNaturalImmunity: Optional[
        list[InstanceOf[seededImmunity]]
    ] = Field(
        title = 'Seeded Natural Immunity Parameters', default = None, 
        description = ((
            'Parameters controlling how individuals naturally gain immunity '
            'to the disease without requiring infection or vaccination.'
        ))
    )
    Scenario_Strain: Optional[
        list[InstanceOf[strainParameters]]
    ] = Field(
        title = 'Strain Parameters', default = None, description = ((
            'Parameters defining different strains of the '
            'infection to simulate in the same population.'
        ))
    )
    Scenario_VaccineCoverage: Optional[
        list[InstanceOf[vaccineCoverage]]
    ] = Field(
        title = 'Vaccine Coverage Parameters', default = None, description = (
            'Parameters defining how much of the population receives vaccines.'
        )
    )
    Scenario_VaccineDose: Optional[
        list[InstanceOf[vaccineDose]]
    ] = Field(
        title = 'Vaccine Dose Parameters', default = None, description = ((
            'Parameters defining how many doses of different vaccine types '
            'the population receives, and how often they are administered.'
        ))
    )
    Scenario_VaccineDoseEfficacy: Optional[
        list[InstanceOf[vaccineEfficacy]]
    ] = Field(
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
        if value is None or info.field_name is None: return value
        # Identify duplicates in relevant category properties
        relevantCategories = parameterGetters[info.field_name]
        configuredValues = [relevantCategories(item) for item in value]
        duplicateValues = [
            item for item in set(configuredValues) 
            if configuredValues.count(item) > 1
        ]
        if not duplicateValues:
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
            raise ValidationError((
                'The Flusim configuration file defined multiple '
                f'{info.field_name} objects with the same values for the '
                f'{' and '.join(parameterCategories[info.field_name])} '
                'attribute(s), making it ambiguous which values apply '
                f'to the following categories: {', '.join(clearValues)}. '
                f'Ensure each {info.field_name} object has unique '
                'values for these attributes.'
            ))
        return value
    
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
                raise ValidationError((
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
    parameters: InstanceOf[Parameters] = Field(
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
    parameters: InstanceOf[Parameters] = Field(
        title = 'Parameters', description = (
            'Parameters to modify for this template.'
        )
    )

# Model for defining parameters for override templates or simulations
class overrideParams(BaseModel): 
    parameters: InstanceOf[Parameters] = Field(
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
    override_setting: Optional[InstanceOf[overrideParams]] = Field(
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
    simulations: list[InstanceOf[simulation]] = Field(
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
    # TODO: better default values for stuff the user can't modify
    # TODO: validate that template/community names are correct
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
    shared_overrides: Optional[InstanceOf[overrideParams]] = Field(
        title = 'Shared Overrides', default = None, description = (
            'Parameters that will be applied to all scenarios in the file.'
        )
    )
    community_overrides: Optional[list[InstanceOf[communityOverride]]] = Field(
        title = 'Community Overrides', default = None, description = ((
            'Parameters that will only be applied to '
            'simulations using specific communities'
        ))
    )
    override_templates: Optional[list[InstanceOf[overrideTemplate]]] = Field(
        title = 'Override Templates', default = None, description = ((
            'Templates containing a set of parameters that '
            'can be applied selectively to different scenarios.'
        ))
    )
    simulation_sets: list[InstanceOf[simulationSet]] = Field(
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