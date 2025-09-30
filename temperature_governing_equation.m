% =========================================================================
% MULTI-ZONE POWDER BED TEMPERATURE CONTROL SIMULATION
% =========================================================================
%
% FILENAME: temperature_governing_equation.m
% DATE: 2025
% VERSION: 2.0 - Decoupled Control Implementation
%
% =========================================================================
% DESCRIPTION
% =========================================================================
% This MATLAB script implements and analyzes temperature control for a 
% multi-zone infrared heating system used in powder bed additive 
% manufacturing (e.g., Selective Laser Sintering - SLS).
%
% The code solves the nonlinear temperature governing equation:
%
%   rho*d*cp*(dTi/dt) = epsilon*sum(Fji*uj) + hc[Te - Ti(t)] + epsilon*sigma_B[Te^4 - Ti^4(t)]
%
% Where the terms represent:
% - Heat capacity: rho*d*cp*(dTi/dt)
% - Radiative heating: epsilon*sum(Fji*uj) 
% - Convective heat loss: hc[Te - Ti(t)]
% - Radiative heat loss: epsilon*sigma_B[Te^4 - Ti^4(t)]
%
% =========================================================================
% SYSTEM CONFIGURATION
% =========================================================================
% - 3x3 grid of infrared heating zones (n = 9)
% - 3x3 grid of target areas on powder bed (m = 9)
% - Decoupled control approach (diagonal view factor approximation)
% - Linearized model for control design
%
% =========================================================================
% KEY FEATURES
% =========================================================================
% 1. MULTIPLE SOLUTION APPROACHES:
%    - Coupled system (full view factor matrix)
%    - Decoupled system (diagonal approximation)
%    - Linearized decoupled system (for control design)
%
% 2. COMPREHENSIVE ANALYSIS:
%    - View factor calculations and approximations
%    - Linearization accuracy assessment
%    - Temperature uniformity metrics
%    - Individual PI controller design
%
% 3. VISUALIZATION:
%    - Temperature evolution plots
%    - 2D temperature distribution heatmaps
%    - Uniformity metrics over time
%    - Controller performance analysis
%
% =========================================================================
% THEORETICAL BACKGROUND
% =========================================================================
% The decoupled control approach is based on:
%
% 1. VIEW FACTOR APPROXIMATION:
%    - Full: F = cos^2(theta)/(pi*S^2)
%    - Decoupled: F approx epsilon/(pi*h^2) for diagonal terms only
%
% 2. LINEARIZATION:
%    - T^4(t) approx T0^4 + 4*T0^3*[T(t) - T0]
%    - Affine transformation: T_tilde(t) = k1*T(t) + k2
%
% 3. TRANSFER FUNCTIONS:
%    - Pi(s) = [epsilon/(pi*h^2)]*k1 / (-k1 + rho*d*cp*s)
%    - Independent SISO systems for each zone
%
% 4. CONTROL OBJECTIVE:
%    - Minimize temperature differences: Delta_ij = T_tilde_i(t) - T_tilde_j(t) -> 0
%    - Achieve uniform temperature across powder bed
%
% =========================================================================
% USAGE
% =========================================================================
% Simply run the script:
%   >> temperature_governing_equation
%
% The script will:
% 1. Solve all three system formulations
% 2. Generate comparison plots
% 3. Perform detailed analysis
% 4. Save results to .mat file
%
% =========================================================================
% OUTPUT FILES
% =========================================================================
% - decoupled_temperature_results.mat: Simulation data
% - Multiple figures: Comparative analysis plots
% - Command window: Detailed numerical results
%
% =========================================================================
% PARAMETERS (Easily Modifiable)
% =========================================================================
% Physical properties can be modified in the main function:
% - rho: Powder density (kg/m^3)
% - cp: Specific heat capacity (J/kg*K)  
% - d: Layer thickness (m)
% - hc: Convective heat transfer coefficient (W/m^2*K)
% - epsilon: Emissivity
% - Te: Ambient temperature (K)
% - T0: Working temperature (K)
%
% Geometric parameters:
% - grid_spacing: Distance between zones (m)
% - h: Heater height above powder bed (m)
%
% =========================================================================

function main_simulation()
    % =========================================================================
    % TEMPERATURE GOVERNING EQUATION FOR MULTI-ZONE POWDER BED HEATING SYSTEM
    % =========================================================================
    % 
    % This function implements the temperature governing equation for a powder bed
    % additive manufacturing system with multiple infrared heating zones.
    %
    % GOVERNING EQUATION:
    % rho*d*cp*(dTi/dt) = epsilon*sum(Fji*uj) + hc[Te - Ti(t)] + epsilon*sigma_B[Te^4 - Ti^4(t)]
    %
    % Where:
    % - rho: powder density (kg/m^3)
    % - d: layer thickness (m)
    % - cp: specific heat capacity (J/kg*K)
    % - Ti(t): temperature of target area i (K)
    % - epsilon: emissivity (dimensionless)
    % - Fji: view factor from heating zone j to target area i
    % - uj: radiation power of heating zone j (W/m^2)
    % - hc: convective heat transfer coefficient (W/m^2*K)
    % - Te: ambient temperature (K)
    % - sigma_B: Stefan-Boltzmann constant (W/m^2*K^4)
    %
    % The code implements both:
    % 1. Coupled system (full view factor matrix)
    % 2. Decoupled system (diagonal approximation for independent control)
    %
    % DATE: 2025
    % =========================================================================
    
    % Clear workspace and command window for clean execution
    clear; clc; close all;
    
    %% =====================================================================
    %% PHYSICAL PARAMETERS DEFINITION
    %% =====================================================================
    % Define all physical parameters for the powder bed heating system
    % These parameters are typical for titanium powder processing
    
    % Material properties (powder characteristics)
    rho = 4500;          % Powder density (kg/m^3) - titanium powder Ti-6Al-4V
    cp = 520;            % Specific heat capacity (J/kg*K) - titanium powder
    d = 30e-6;           % Layer thickness (m) - 30 micrometers (typical SLS layer)
    
    % Heat transfer parameters
    hc = 10;             % Convective heat transfer coefficient (W/m^2*K)
                         % Typical for natural convection in powder bed
    epsilon = 0.8;       % Emissivity (dimensionless) - oxidized titanium surface
    sigma_B = 5.67e-8;   % Stefan-Boltzmann constant (W/m^2*K^4) - physical constant
    
    % Environmental and operating conditions
    Te = 300;            % Ambient temperature (K) - room temperature (27degC)
    T0 = 473;            % Working/set-point preheating temperature (K) - 200degC
                         % This is the target temperature for powder preheating
    
    % System configuration for 3x3 grid layout
    n = 9;               % Number of heating zones (3x3 grid)
    m = 9;               % Number of target areas on powder bed (equal to heating zones)
    
    
    %% =====================================================================
    %% GEOMETRIC CONFIGURATION SETUP
    %% =====================================================================
    % Define the spatial layout of heating zones and target areas
    % Creates a 3x3 grid arrangement for uniform coverage
    
    % Grid parameters
    grid_spacing = 0.01;  % 1 cm spacing between adjacent zones
    h = 0.005;           % Height of heating zones above powder bed (5 mm)
                         % This height affects view factors and heat distribution
    
    % Generate 3x3 grid coordinates using meshgrid
    % This creates a uniform spatial distribution
    [X_h, Y_h] = meshgrid(0:grid_spacing:2*grid_spacing, 0:grid_spacing:2*grid_spacing);
    
    % Heating zone positions (x, y, z) in meters
    % All heaters are at height h above the powder bed
    heater_pos = [X_h(:), Y_h(:), h*ones(9,1)];
    
    % Target area positions (x, y, z) on powder bed
    % Aligned directly below each heater (z = 0 for powder bed surface)
    target_pos = [X_h(:), Y_h(:), zeros(9,1)];
    
    % Display configuration information
    fprintf('=== 3x3 GRID CONFIGURATION ===\n');
    fprintf('Grid spacing: %.3f m (%.1f cm)\n', grid_spacing, grid_spacing*100);
    fprintf('Heater height: %.3f m (%.1f mm)\n', h, h*1000);
    fprintf('Total coverage area: %.1f x %.1f cm^2\n', 2*grid_spacing*100, 2*grid_spacing*100);
    
    
    %% =====================================================================
    %% VIEW FACTOR CALCULATIONS
    %% =====================================================================
    % Calculate view factors between heating zones and target areas
    % View factors determine how much radiation from each heater reaches each target
    %
    % VIEW FACTOR FORMULA: F = cos^2(theta)/(pi*S^2)
    % Where:
    % - theta: angle between surface normal and line connecting heater to target
    % - S: distance between heater and target
    %
    % For decoupled control, we use diagonal approximation: F approx epsilon/(pi*h^2)
    
    F_full = zeros(n, m);  % Full view factor matrix (nxm) - all interactions
    F_diag = zeros(n, 1);  % Diagonal view factors only (for decoupled system)
    
    % Calculate view factors for all heater-target combinations
    fprintf('\n=== CALCULATING VIEW FACTORS ===\n');
    for j = 1:n  % Loop through all heating zones
        for i = 1:m  % Loop through all target areas
            
            % Calculate 3D distance vector between heater j and target i
            dx = heater_pos(j,1) - target_pos(i,1);  % x-direction distance
            dy = heater_pos(j,2) - target_pos(i,2);  % y-direction distance
            dz = heater_pos(j,3) - target_pos(i,3);  % z-direction distance (height)
            
            % Total 3D distance
            S = sqrt(dx^2 + dy^2 + dz^2);
            
            % Calculate angle theta between surface normal and connecting line
            % For parallel surfaces: theta = arctan(horizontal_distance / vertical_distance)
            theta = atan(sqrt(dx^2 + dy^2) / abs(dz));
            
            % Apply view factor formula: F = cos^2(theta)/(pi*S^2)
            F_full(j,i) = (cos(theta))^2 / (pi * S^2);
            
            % Store diagonal terms (self-heating: heater i -> target i)
            if j == i
                F_diag(j) = F_full(j,i);
            end
        end
    end
    
    % Calculate decoupled approximation: F = epsilon/(pi*h^2)
    % This assumes each heater only affects its directly aligned target area
    % Note: This should be a dimensionless view factor, not involving epsilon
    F_decoupled = 1 / (pi * h^2) * ones(n,1);
    
    % Display view factor information
    fprintf('Diagonal View Factors (exact geometric calculation):\n');
    for i = 1:n
        fprintf('F_%d%d = %.6f\n', i, i, F_diag(i));
    end
    
    fprintf('\nDecoupled Approximation: F = 1/(pi*h^2) = %.6f\n', F_decoupled(1));
    fprintf('Approximation error: %.2f%%\n', abs(F_decoupled(1) - F_diag(1))/F_diag(1)*100);
    
    
    %% =====================================================================
    %% SIMULATION SETUP AND TIME PARAMETERS
    %% =====================================================================
    % Define simulation time span and initial conditions
    
    % Time parameters
    t_start = 0;         % Start time (s)
    t_end = 10;          % End time (s) - 10 seconds for demonstration
    tspan = [t_start t_end];
    
    % Initial temperature conditions
    % All target areas start at the working temperature T0
    T_initial = T0 * ones(m, 1);  % Initial temperature vector (K)
    
    fprintf('\n=== SIMULATION PARAMETERS ===\n');
    fprintf('Simulation time: %.1f seconds\n', t_end);
    fprintf('Initial temperature: %.1f K (%.1f degC)\n', T0, T0-273.15);
    fprintf('Number of zones: %d\n', n);
    
    
    %% =====================================================================
    %% SOLVE DIFFERENTIAL EQUATIONS - MULTIPLE APPROACHES
    %% =====================================================================
    % Solve the temperature governing equation using three different approaches:
    % 1. Coupled system (full view factor matrix) - accounts for all interactions
    % 2. Decoupled system (diagonal approximation) - independent zone control
    % 3. Linearized decoupled system - for control design
    
    % APPROACH 1: COUPLED SYSTEM
    % Uses full view factor matrix - each target receives heat from all heaters
    fprintf('\n=== SOLVING COUPLED (FULL) SYSTEM ===\n');
    fprintf('- Accounts for all heater-target interactions\n');
    fprintf('- Uses complete view factor matrix\n');
    ode_func_coupled = @(t, T) temperature_ode_coupled(t, T, rho, cp, d, hc, epsilon, sigma_B, Te, F_full, n);
    
    % Use more robust ODE solver options
    options = odeset('RelTol', 1e-6, 'AbsTol', 1e-8, 'MaxStep', 0.1);
    [t_coupled, T_coupled] = ode45(ode_func_coupled, tspan, T_initial, options);
    
    % APPROACH 2: DECOUPLED SYSTEM  
    % Uses diagonal approximation - each target only receives heat from its corresponding heater
    fprintf('\n=== SOLVING DECOUPLED SYSTEM ===\n');
    fprintf('- Each zone controlled independently\n');
    fprintf('- Uses diagonal view factor approximation\n');
    ode_func_decoupled = @(t, T) temperature_ode_decoupled(t, T, rho, cp, d, hc, epsilon, sigma_B, Te, F_decoupled, n);
    [t_decoupled, T_decoupled] = ode45(ode_func_decoupled, tspan, T_initial, options);
    
    % APPROACH 3: LINEARIZED DECOUPLED SYSTEM
    % Linearizes the nonlinear radiation term for control design
    fprintf('\n=== SOLVING LINEARIZED DECOUPLED SYSTEM ===\n');
    fprintf('- Linearized around working temperature T0\n');
    fprintf('- Suitable for linear control design\n');
    
    % Get linearized state-space matrices
    [A_dec, B_dec, C_dec, k1, k2] = get_decoupled_system(rho, cp, d, hc, epsilon, sigma_B, Te, T0, h, n);
    
    % Transform initial conditions to affined temperature space
    % T_tilde(t) = k1*T(t) + k2 (affine transformation for linearization)
    T_tilde_initial = k1 * T_initial + k2;
    
    % Solve linearized system in transformed coordinates
    ode_func_linear_dec = @(t, T_tilde) A_dec * T_tilde + B_dec * get_heating_power(t, n);
    [t_lin_dec, T_tilde_lin_dec] = ode45(ode_func_linear_dec, tspan, T_tilde_initial, options);
    
    % Transform back to actual temperatures
    % T(t) = (T_tilde(t) - k2) / k1
    T_lin_dec = (T_tilde_lin_dec - k2) / k1;
    
    
    %% =====================================================================
    %% RESULTS ANALYSIS AND VISUALIZATION
    %% =====================================================================
    % Analyze and visualize the results from all three solution approaches
    
    % Generate comprehensive comparison plots
    fprintf('\n=== GENERATING RESULTS VISUALIZATION ===\n');
    plot_decoupled_results(t_coupled, T_coupled, t_decoupled, T_decoupled, t_lin_dec, T_lin_dec, m);
    
    % Analyze temperature uniformity (key performance metric for powder bed heating)
    fprintf('\n=== ANALYZING TEMPERATURE UNIFORMITY ===\n');
    analyze_temperature_uniformity(t_coupled, T_coupled, t_decoupled, T_decoupled, m);
    
    % Display summary of final results
    fprintf('\n=== FINAL RESULTS COMPARISON ===\n');
    for i = 1:min(5,m)  % Show first 5 zones to avoid excessive output
        fprintf('Zone %d:\n', i);
        fprintf('  Coupled    - Initial: %.2f K, Final: %.2f K (Change: %+.2f K)\n', ...
                T_coupled(1,i), T_coupled(end,i), T_coupled(end,i) - T_coupled(1,i));
        fprintf('  Decoupled  - Initial: %.2f K, Final: %.2f K (Change: %+.2f K)\n', ...
                T_decoupled(1,i), T_decoupled(end,i), T_decoupled(end,i) - T_decoupled(1,i));
        fprintf('  Linear Dec - Initial: %.2f K, Final: %.2f K (Change: %+.2f K)\n', ...
                T_lin_dec(1,i), T_lin_dec(end,i), T_lin_dec(end,i) - T_lin_dec(1,i));
        fprintf('  Coupled vs Decoupled difference: %.3f K\n', abs(T_coupled(end,i) - T_decoupled(end,i)));
        fprintf('\n');
    end
    
    % Save all results to MATLAB data file for further analysis
    fprintf('=== SAVING RESULTS ===\n');
    save('decoupled_temperature_results.mat', 't_coupled', 'T_coupled', 't_decoupled', 'T_decoupled', ...
         't_lin_dec', 'T_lin_dec', 'F_full', 'F_decoupled', 'heater_pos', 'target_pos');
    fprintf('Results saved to: decoupled_temperature_results.mat\n');
end

% =========================================================================
% SUPPORTING FUNCTIONS
% =========================================================================

function dTdt = temperature_ode_coupled(t, T, rho, cp, d, hc, epsilon, sigma_B, Te, F_full, n)
    % =====================================================================
    % COUPLED SYSTEM ODE FUNCTION
    % =====================================================================
    % Solves the full nonlinear temperature governing equation with coupling
    % between all heating zones and target areas.
    %
    % INPUTS:
    %   t       - Current time (s)
    %   T       - Temperature vector for all target areas (K)
    %   rho     - Powder density (kg/m^3)
    %   cp      - Specific heat capacity (J/kg*K)
    %   d       - Layer thickness (m)
    %   hc      - Convective heat transfer coefficient (W/m^2*K)
    %   epsilon - Emissivity (dimensionless)
    %   sigma_B - Stefan-Boltzmann constant (W/m^2*K^4)
    %   Te      - Ambient temperature (K)
    %   F_full  - Full view factor matrix (nxm)
    %   n       - Number of heating zones
    %
    % OUTPUT:
    %   dTdt    - Temperature derivatives (dT/dt) for all target areas
    %
    % GOVERNING EQUATION:
    % rho*d*cp*(dTi/dt) = epsilon*sum(Fji*uj) + hc[Te - Ti] + epsilon*sigma_B[Te^4 - Ti^4]
    % =====================================================================
    
    m = length(T);           % Number of target areas
    dTdt = zeros(m, 1);      % Initialize derivative vector
    
    % Get current heating power for all zones
    u = get_heating_power(t, n);
    
    % Calculate temperature derivative for each target area
    for i = 1:m
        % HEAT INPUT: Sum of radiation from all heating zones (coupling effect)
        % Each target area receives heat from ALL heating zones, weighted by view factors
        q_input = epsilon * sum(F_full(:,i) .* u);
        
        % CONVECTIVE HEAT TRANSFER: Heat exchange with ambient air
        % Positive when ambient is warmer, negative when target is warmer
        q_conv = hc * (Te - T(i));
        
        % RADIATIVE HEAT TRANSFER: Heat exchange with ambient via radiation
        % Follows Stefan-Boltzmann law: q = epsilon*sigma*(Te^4 - T^4)
        q_rad = epsilon * sigma_B * (Te^4 - T(i)^4);
        
        % ENERGY BALANCE: Apply first law of thermodynamics
        % rho*d*cp*(dT/dt) = q_total
        dTdt(i) = (1/(rho * d * cp)) * (q_input + q_conv + q_rad);
        
        % Check for numerical stability
        if isnan(dTdt(i)) || isinf(dTdt(i))
            warning('Numerical instability detected in coupled system at zone %d, time %.3f', i, t);
            dTdt(i) = 0;  % Set to zero to prevent further divergence
        end
    end
end

function dTdt = temperature_ode_decoupled(t, T, rho, cp, d, hc, epsilon, sigma_B, Te, F_decoupled, n)
    % =====================================================================
    % DECOUPLED SYSTEM ODE FUNCTION
    % =====================================================================
    % Solves the temperature governing equation with decoupling approximation.
    % Each target area only receives heat from its corresponding heating zone.
    % This simplification enables independent control of each zone.
    %
    % DECOUPLING ASSUMPTION:
    % - Off-diagonal view factors approx 0 (neglect cross-coupling)
    % - Each heater only affects its aligned target area
    % - Enables parallel controller design for each zone
    %
    % ADVANTAGES:
    % - Simplified control design (9 independent SISO systems)
    % - Reduced computational complexity
    % - Parallel implementation possible
    %
    % DISADVANTAGES:
    % - Ignores thermal coupling between zones
    % - May introduce control errors in tightly coupled systems
    % =====================================================================
    
    m = length(T);           % Number of target areas
    dTdt = zeros(m, 1);      % Initialize derivative vector
    
    % Get current heating power for all zones
    u = get_heating_power(t, n);
    
    % Calculate temperature derivative for each target area
    for i = 1:m
        % HEAT INPUT: Only from corresponding heating zone (decoupled)
        % Zone i only receives heat from heater i
        if i <= n
            q_input = epsilon * F_decoupled(i) * u(i);  % Self-heating only
        else
            q_input = 0;  % No corresponding heater
        end
        
        % CONVECTIVE HEAT TRANSFER: Same as coupled system
        q_conv = hc * (Te - T(i));
        
        % RADIATIVE HEAT TRANSFER: Same as coupled system
        q_rad = epsilon * sigma_B * (Te^4 - T(i)^4);
        
        % ENERGY BALANCE: Apply first law of thermodynamics
        dTdt(i) = (1/(rho * d * cp)) * (q_input + q_conv + q_rad);
        
        % Check for numerical stability
        if isnan(dTdt(i)) || isinf(dTdt(i))
            warning('Numerical instability detected in decoupled system at zone %d, time %.3f', i, t);
            dTdt(i) = 0;  % Set to zero to prevent further divergence
        end
    end
end

function [A, B, C, k1, k2] = get_decoupled_system(rho, cp, d, hc, epsilon, sigma_B, Te, T0, h, n)
    % =====================================================================
    % LINEARIZED DECOUPLED STATE-SPACE MODEL GENERATION
    % =====================================================================
    % Generates state-space matrices for the linearized decoupled system.
    % Linearization is performed around the working temperature T0.
    %
    % LINEARIZATION PROCESS:
    % 1. Nonlinear term: T^4(t) approx T0^4 + 4*T0^3*[T(t) - T0]
    % 2. Affine transformation: T_tilde(t) = k1*T(t) + k2
    % 3. Results in linear state-space: dT_tilde/dt = A*T_tilde + B*u
    %
    % STATE-SPACE FORM:
    % dx/dt = Ax + Bu  (state equation)
    % y = Cx           (output equation)
    %
    % Where:
    % x = T_tilde (affined temperature vector)
    % u = heating power vector
    % y = measured temperatures
    %
    % DECOUPLED STRUCTURE:
    % - A matrix: diagonal (no state coupling)
    % - B matrix: diagonal (independent inputs)
    % - Results in n independent SISO transfer functions
    % =====================================================================
    
    % LINEARIZATION COEFFICIENTS
    % k1 captures the effect of convection and linearized radiation
    k1 = -(hc + 4*epsilon*sigma_B*T0^3);  % Always negative (stable)
    
    % k2 captures the ambient temperature effects and constant radiation terms
    k2 = hc*Te + epsilon*sigma_B*Te^4 + 3*epsilon*sigma_B*T0^4;
    
    % STATE MATRIX A (nxn diagonal matrix)
    % Each diagonal element: a_ii = k1/(rho*d*cp)
    % Represents thermal time constants for each zone
    A = (k1/(rho*d*cp)) * eye(n);
    
    % INPUT MATRIX B (nxn diagonal matrix for decoupled system)
    % Each diagonal element: b_ii = (1/(pi*h^2)) / (rho*d*cp)
    % Represents input gain from heating power to temperature
    B = (1/(pi*h^2)) / (rho*d*cp) * eye(n);
    
    % OUTPUT MATRIX C (nxn identity matrix)
    % Direct measurement of all state variables (temperatures)
    C = eye(n);
    
    % Display system characteristics
    fprintf('Linearized System Characteristics:\n');
    fprintf('k1 coefficient: %.6f (stability parameter)\n', k1);
    fprintf('k2 coefficient: %.6f (ambient effects)\n', k2);
    fprintf('Time constant tau = rho*d*cp/|k1| = %.4f s\n', (rho*d*cp)/abs(k1));
    fprintf('Input gain: %.6e\n', (1/(pi*h^2)) / (rho*d*cp));
end

function u = get_heating_power(t, n)
    % =====================================================================
    % HEATING POWER PROFILE GENERATOR
    % =====================================================================
    % Generates time-varying heating power profiles for all heating zones.
    % Designed to test system response and temperature uniformity control.
    %
    % POWER PROFILE PHASES:
    % 1. Ramp-up (0-2s): Gradual power increase to avoid thermal shock
    % 2. Steady (2-6s): Constant power with small variations to test control
    % 3. Ramp-down (6-10s): Gradual power decrease to simulate process end
    %
    % DESIGN RATIONALE:
    % - Different base powers create temperature gradients
    % - Small sinusoidal variations test disturbance rejection
    % - Smooth transitions prevent unrealistic power jumps
    % - Realistic power levels for IR heating systems (1-2 kW/m^2)
    % =====================================================================
    
    u = zeros(n, 1);  % Initialize power vector
    
    % BASE POWER LEVELS (W/m^2)
    % Deliberately varied to create temperature gradients for testing uniformity control
    % Reduced to more realistic levels to prevent numerical instability
    base_powers = [1000, 1050, 950, 1025, 1000, 975, 1037, 987, 1012];  % W/m^2
    
    % Ensure array compatibility with number of zones
    base_powers = base_powers(1:min(n, length(base_powers)));
    if n > length(base_powers)
        % Extend with nominal power for additional zones
        base_powers = [base_powers, 1000*ones(1, n-length(base_powers))];
    end
    
    % TIME-DEPENDENT POWER PROFILES
    if t <= 2
        % PHASE 1: RAMP-UP (0-2 seconds)
        % Linear increase from 0 to full power to avoid thermal shock
        u = base_powers' * (t/2);
        
    elseif t <= 6
        % PHASE 2: STEADY STATE WITH DISTURBANCES (2-6 seconds)
        % Constant power with small sinusoidal variations
        % Each zone has different frequency to simulate realistic disturbances
        disturbance_factor = 1 + 0.1*sin(2*pi*t*[1:n]'/n);  % +/-10% variation
        u = base_powers' .* disturbance_factor;
        
    else
        % PHASE 3: RAMP-DOWN (6-10 seconds)
        % Linear decrease to simulate process termination
        factor = max(0, (10-t)/4);  % Linear decay to zero
        u = base_powers' * factor;
    end
    
    % Ensure non-negative power (physical constraint)
    u = max(u, 0);
end

function plot_decoupled_results(t_coupled, T_coupled, t_decoupled, T_decoupled, t_lin_dec, T_lin_dec, m)
    % =====================================================================
    % COMPREHENSIVE RESULTS VISUALIZATION
    % =====================================================================
    % Creates a comprehensive visualization comparing all three solution approaches:
    % 1. Coupled system (full interactions)
    % 2. Decoupled system (independent zones)  
    % 3. Linearized decoupled system (for control design)
    %
    % VISUALIZATION COMPONENTS:
    % - Individual zone temperature evolution
    % - Temperature uniformity metrics over time
    % - Final temperature distribution as 2D heatmaps
    % - Quantitative comparison of approaches
    % =====================================================================
    
    % Create large figure with multiple subplots
    figure('Position', [100, 100, 1400, 1000], 'Name', 'Multi-Zone Temperature Control Comparison');
    
    % SELECT REPRESENTATIVE ZONES FOR DETAILED PLOTTING
    % Choose corner, edge, and center zones to show different behaviors
    zones_to_plot = [1, 2, 3, 5, 7, 9];  % Zones: corner, edge, center positions
    zone_labels = {'Corner 1', 'Edge 1', 'Corner 2', 'Center', 'Edge 2', 'Corner 3'};
    
    % PLOT INDIVIDUAL ZONE TEMPERATURE EVOLUTION
    for idx = 1:length(zones_to_plot)
        i = zones_to_plot(idx);
        subplot(3, 3, idx);
        
        % Plot all three approaches
        plot(t_coupled, T_coupled(:,i), 'b-', 'LineWidth', 2); hold on;
        plot(t_decoupled, T_decoupled(:,i), 'r--', 'LineWidth', 2);
        plot(t_lin_dec, T_lin_dec(:,i), 'g:', 'LineWidth', 2);
        
        xlabel('Time (s)');
        ylabel('Temperature (K)');
        title(sprintf('Zone %d (%s)', i, zone_labels{idx}));
        legend('Coupled', 'Decoupled', 'Linear Dec', 'Location', 'best');
        grid on;
        
        % Add temperature range annotation
        T_range = max(T_coupled(:,i)) - min(T_coupled(:,i));
        text(0.05, 0.95, sprintf('Range: %.2f K', T_range), ...
             'Units', 'normalized', 'VerticalAlignment', 'top');
    end
    
    % PLOT TEMPERATURE UNIFORMITY EVOLUTION
    subplot(3, 3, 7);
    % Calculate standard deviation across all zones (uniformity metric)
    std_coupled = std(T_coupled, 0, 2, 'omitnan');      % Standard deviation over zones, omit NaN
    std_decoupled = std(T_decoupled, 0, 2);
    std_lin_dec = std(T_lin_dec, 0, 2);
    
    plot(t_coupled, std_coupled, 'b-', 'LineWidth', 2); hold on;
    plot(t_decoupled, std_decoupled, 'r--', 'LineWidth', 2);
    plot(t_lin_dec, std_lin_dec, 'g:', 'LineWidth', 2);
    
    xlabel('Time (s)');
    ylabel('Temperature Std Dev (K)');
    title('Temperature Uniformity (Lower = Better)');
    legend('Coupled', 'Decoupled', 'Linear Dec', 'Location', 'best');
    grid on;
    
    % Add uniformity target line
    yline(0.5, 'k:', 'Target < 0.5 K', 'LineWidth', 1);
    
    % PLOT FINAL TEMPERATURE DISTRIBUTION - COUPLED SYSTEM
    subplot(3, 3, 8);
    T_final_coupled = reshape(T_coupled(end, 1:9), 3, 3);  % Reshape to 3x3 grid
    
    % Check for NaN values and handle appropriately
    if any(isnan(T_final_coupled(:)))
        % If NaN values present, show error message
        text(0.5, 0.5, 'Coupled System Diverged (NaN)', 'HorizontalAlignment', 'center', ...
             'Units', 'normalized', 'FontSize', 12, 'Color', 'red', 'FontWeight', 'bold');
        title('Final Temperature - Coupled (DIVERGED)');
        axis off;
    else
        imagesc(T_final_coupled);
        colorbar;
        colormap(gca, 'hot');  % Use temperature-appropriate colormap
        title('Final Temperature - Coupled (K)');
        xlabel('X Position'); ylabel('Y Position');
        axis equal tight;
        
        % Add temperature values as text overlay
        for i = 1:3
            for j = 1:3
                text(j, i, sprintf('%.1f', T_final_coupled(i,j)), ...
                     'HorizontalAlignment', 'center', 'Color', 'white', 'FontWeight', 'bold');
            end
        end
    end
    
    % PLOT FINAL TEMPERATURE DISTRIBUTION - DECOUPLED SYSTEM
    subplot(3, 3, 9);
    T_final_decoupled = reshape(T_decoupled(end, 1:9), 3, 3);
    imagesc(T_final_decoupled);
    colorbar;
    colormap(gca, 'hot');
    title('Final Temperature - Decoupled (K)');
    xlabel('X Position'); ylabel('Y Position');
    axis equal tight;
    
    % Add temperature values as text overlay
    for i = 1:3
        for j = 1:3
            text(j, i, sprintf('%.1f', T_final_decoupled(i,j)), ...
                 'HorizontalAlignment', 'center', 'Color', 'white', 'FontWeight', 'bold');
        end
    end
    
    % Add overall title
    sgtitle('Decoupled vs Coupled Multi-Zone Temperature Control Analysis', 'FontSize', 14);
    
    % Print summary statistics
    fprintf('=== VISUALIZATION SUMMARY ===\n');
    fprintf('Final temperature uniformity (std dev):\n');
    
    % Handle NaN values in statistics
    if any(isnan(T_coupled(end,:)))
        fprintf('  Coupled:    DIVERGED (NaN values)\n');
    else
        fprintf('  Coupled:    %.3f K\n', std_coupled(end));
    end
    
    fprintf('  Decoupled:  %.3f K\n', std_decoupled(end));
    fprintf('  Linear Dec: %.3f K\n', std_lin_dec(end));
end

function analyze_temperature_uniformity(t_coupled, T_coupled, t_decoupled, T_decoupled, m)
    % Analyze temperature uniformity metrics
    
    fprintf('\nTemperature Uniformity Analysis:\n');
    
    % Calculate metrics at final time
    T_final_coupled = T_coupled(end, 1:min(9,m));
    T_final_decoupled = T_decoupled(end, 1:min(9,m));
    
    % Standard deviation (lower is better)
    std_coupled = std(T_final_coupled);
    std_decoupled = std(T_final_decoupled);
    
    % Range (max - min)
    range_coupled = max(T_final_coupled) - min(T_final_coupled);
    range_decoupled = max(T_final_decoupled) - min(T_final_decoupled);
    
    % Temperature differences between adjacent zones (for 3x3 grid)
    if m >= 9
        delta_ij_coupled = calculate_temperature_differences(T_final_coupled);
        delta_ij_decoupled = calculate_temperature_differences(T_final_decoupled);
        
        fprintf('Temperature Uniformity Metrics:\n');
        fprintf('                    Coupled    Decoupled   Improvement\n');
        fprintf('Std Deviation (K):  %.3f      %.3f       %.1f%%\n', ...
                std_coupled, std_decoupled, (std_coupled-std_decoupled)/std_coupled*100);
        fprintf('Range (K):          %.3f      %.3f       %.1f%%\n', ...
                range_coupled, range_decoupled, (range_coupled-range_decoupled)/range_coupled*100);
        fprintf('Max |DeltaT_ij| (K):    %.3f      %.3f       %.1f%%\n', ...
                max(abs(delta_ij_coupled)), max(abs(delta_ij_decoupled)), ...
                (max(abs(delta_ij_coupled))-max(abs(delta_ij_decoupled)))/max(abs(delta_ij_coupled))*100);
        
        % Check convergence criterion: Delta_ij -> 0
        fprintf('\nConvergence Analysis (|T_i - T_j| for adjacent zones):\n');
        fprintf('Coupled system max difference: %.4f K\n', max(abs(delta_ij_coupled)));
        fprintf('Decoupled system max difference: %.4f K\n', max(abs(delta_ij_decoupled)));
        
        if max(abs(delta_ij_decoupled)) < 0.1
            fprintf('SUCCESS: Decoupled control achieves good uniformity (< 0.1 K difference)\n');
        else
            fprintf('WARNING: Temperature differences still significant\n');
        end
    end
end

function delta_ij = calculate_temperature_differences(T_grid_vector)
    % Calculate temperature differences between adjacent zones in 3x3 grid
    
    if length(T_grid_vector) < 9
        delta_ij = [];
        return;
    end
    
    % Reshape to 3x3 grid
    T_grid = reshape(T_grid_vector(1:9), 3, 3);
    
    delta_ij = [];
    
    % Horizontal differences
    for i = 1:3
        for j = 1:2
            delta_ij = [delta_ij, T_grid(i,j) - T_grid(i,j+1)];
        end
    end
    
    % Vertical differences
    for i = 1:2
        for j = 1:3
            delta_ij = [delta_ij, T_grid(i,j) - T_grid(i+1,j)];
        end
    end
end

function analyze_view_factors()
    % Analyze the effect of different geometries on view factors
    
    fprintf('\nView Factor Analysis:\n');
    
    % Test different distances
    distances = [0.005, 0.01, 0.02, 0.05];  % meters
    
    fprintf('View Factor vs Distance (theta = 0 deg):\n');
    for i = 1:length(distances)
        S = distances(i);
        theta = 0;  % directly above
        F = (cos(theta))^2 / (pi * S^2);
        fprintf('Distance: %.3f m, View Factor: %.6f\n', S, F);
    end
    
    % Test different angles
    angles = [0, 15, 30, 45, 60] * pi/180;  % radians
    S = 0.01;  % fixed distance
    
    fprintf('\nView Factor vs Angle (S = %.3f m):\n', S);
    for i = 1:length(angles)
        theta = angles(i);
        F = (cos(theta))^2 / (pi * S^2);
        fprintf('Angle: %.1f deg, View Factor: %.6f\n', theta*180/pi, F);
    end
end

function analyze_linearization_accuracy()
    % Analyze the accuracy of the linearization approximation
    
    T0 = 473;  % Working temperature (K)
    epsilon = 0.8;
    sigma_B = 5.67e-8;
    
    % Temperature range around working point
    T_range = (T0-50):5:(T0+50);
    
    % Exact nonlinear term
    T4_exact = T_range.^4;
    
    % Linearized approximation
    T4_linear = T0^4 + 4*T0^3*(T_range - T0);
    
    % Calculate relative error
    rel_error = abs(T4_exact - T4_linear) ./ T4_exact * 100;
    
    figure('Position', [300, 300, 800, 400]);
    
    subplot(1,2,1);
    plot(T_range, T4_exact/1e9, 'b-', 'LineWidth', 2); hold on;
    plot(T_range, T4_linear/1e9, 'r--', 'LineWidth', 2);
    xlabel('Temperature (K)');
    ylabel('T^4 (x10^9 K^4)');
    title('T^4 Term: Exact vs Linearized');
    legend('Exact', 'Linearized', 'Location', 'best');
    grid on;
    
    subplot(1,2,2);
    plot(T_range, rel_error, 'k-', 'LineWidth', 2);
    xlabel('Temperature (K)');
    ylabel('Relative Error (%)');
    title('Linearization Error');
    grid on;
    
    fprintf('\nLinearization Analysis around T0 = %.1f K:\n', T0);
    fprintf('Max relative error in +/-50K range: %.2f%%\n', max(rel_error));
    fprintf('Error at +/-10K: %.3f%%, %.3f%%\n', ...
        rel_error(T_range == T0-10), rel_error(T_range == T0+10));
end

function design_decoupled_controllers()
    % Design individual controllers for each zone in the decoupled system
    % Based on transfer function Pi(s) = (epsilon/(pi*h^2)) / (-k1 + rho*d*cp*s)
    
    % System parameters
    rho = 4500; cp = 520; d = 30e-6; hc = 10;
    epsilon = 0.8; sigma_B = 5.67e-8; Te = 300; T0 = 473;
    h = 0.005;  % heater height
    
    % Linearization coefficients
    k1 = -(hc + 4*epsilon*sigma_B*T0^3);
    
    % Transfer function parameters
    K_p = 1 / (pi * h^2);  % Process gain (corrected - removed epsilon)
    tau = rho * d * cp / (-k1);  % Time constant
    
    fprintf('\nDecoupled Controller Design:\n');
    fprintf('Process gain K_p = %.6f\n', K_p);
    fprintf('Time constant tau = %.4f s\n', tau);
    fprintf('Transfer function: P(s) = %.6f / (%.4f*s + 1)\n', K_p/tau, tau);
    
    % Design PI controllers for each zone
    % Target: 2% settling time = 4*tau_cl, where tau_cl = desired closed-loop time constant
    tau_cl_desired = 1.0;  % 1 second desired closed-loop time constant
    
    % PI controller design using pole placement
    % Desired characteristic equation: s^2 + 2*zeta*wn*s + wn^2 = 0
    % With zeta = 0.707 (critically damped), wn = 1/tau_cl_desired
    zeta = 0.707;
    wn = 1 / tau_cl_desired;
    
    % Controller parameters
    Kp_controller = (2*zeta*wn*tau - 1) / K_p;
    Ki_controller = wn^2 * tau / K_p;
    
    fprintf('\nPI Controller Parameters:\n');
    fprintf('Proportional gain Kp = %.4f\n', Kp_controller);
    fprintf('Integral gain Ki = %.4f\n', Ki_controller);
    fprintf('Controller: C(s) = %.4f + %.4f/s\n', Kp_controller, Ki_controller);
    
    % Closed-loop analysis
    fprintf('\nClosed-loop Performance:\n');
    fprintf('Natural frequency wn = %.3f rad/s\n', wn);
    fprintf('Damping ratio zeta = %.3f\n', zeta);
    fprintf('Settling time (2%%) approx %.2f s\n', 4*tau_cl_desired);
    
    % Simulate step response of one zone
    simulate_single_zone_control(K_p, tau, Kp_controller, Ki_controller);
end

function simulate_single_zone_control(K_p, tau, Kp, Ki)
    % Simulate step response of a single zone with PI control
    
    % Transfer functions
    s = tf('s');
    P = K_p / (tau*s + 1);              % Process
    C = pid(Kp, Ki);                    % PI controller
    T_cl = feedback(C*P, 1);            % Closed-loop
    
    % Step response
    figure('Position', [400, 400, 800, 400]);
    
    subplot(1,2,1);
    step(T_cl, 10);
    title('Closed-loop Step Response');
    ylabel('Temperature Response');
    grid on;
    
    subplot(1,2,2);
    step(C*P/(1+C*P), 10);  % Control effort
    title('Control Effort (Heating Power)');
    ylabel('Normalized Power');
    grid on;
    
    % Calculate performance metrics
    info = stepinfo(T_cl);
    fprintf('\nStep Response Performance:\n');
    fprintf('Rise time: %.3f s\n', info.RiseTime);
    fprintf('Settling time: %.3f s\n', info.SettlingTime);
    fprintf('Overshoot: %.2f%%\n', info.Overshoot);
    fprintf('Peak time: %.3f s\n', info.PeakTime);
end

function analyze_decoupling_approximation()
    % Analyze the validity of the decoupling approximation
    
    fprintf('\nDecoupling Approximation Analysis:\n');
    
    % Example 3x3 grid parameters
    grid_spacing = 0.01;  % 1 cm
    h = 0.005;           % 5 mm height
    
    % Calculate view factors for center zone (zone 5 in 3x3 grid)
    center_pos = [grid_spacing, grid_spacing, 0];
    
    % View factor from center heater to center target (diagonal term)
    F_diagonal = 1 / (pi * h^2);  % cos^2(0 deg) = 1, S = h
    
    % View factors from adjacent heaters to center target (off-diagonal terms)
    S_adjacent = sqrt(grid_spacing^2 + h^2);
    theta_adjacent = atan(grid_spacing / h);
    F_adjacent = (cos(theta_adjacent))^2 / (pi * S_adjacent^2);
    
    % View factors from corner heaters to center target
    S_corner = sqrt(2*grid_spacing^2 + h^2);
    theta_corner = atan(sqrt(2)*grid_spacing / h);
    F_corner = (cos(theta_corner))^2 / (pi * S_corner^2);
    
    fprintf('View Factors for Center Zone:\n');
    fprintf('Diagonal (self): %.6f\n', F_diagonal);
    fprintf('Adjacent zones:  %.6f (%.1f%% of diagonal)\n', F_adjacent, F_adjacent/F_diagonal*100);
    fprintf('Corner zones:    %.6f (%.1f%% of diagonal)\n', F_corner, F_corner/F_diagonal*100);
    
    % Total coupling effect
    total_coupling = 4*F_adjacent + 4*F_corner;  % 4 adjacent + 4 corner zones
    coupling_ratio = total_coupling / F_diagonal;
    
    fprintf('\nCoupling Analysis:\n');
    fprintf('Total off-diagonal coupling: %.6f\n', total_coupling);
    fprintf('Coupling ratio (off-diag/diagonal): %.3f\n', coupling_ratio);
    
    if coupling_ratio < 0.1
        fprintf('SUCCESS: Decoupling approximation is valid (coupling < 10%%)\n');
    elseif coupling_ratio < 0.2
        fprintf('WARNING: Moderate coupling (10-20%%) - decoupling may introduce some error\n');
    else
        fprintf('WARNING: Strong coupling (>20%%) - decoupling approximation questionable\n');
    end
end

% =========================================================================
% MAIN EXECUTION SECTION
% =========================================================================
% Execute all functions in sequence to perform comprehensive analysis
% of the multi-zone powder bed heating system.
%
% EXECUTION ORDER:
% 1. Main simulation (temperature_governing_equation)
% 2. View factor analysis (geometric relationships)
% 3. Linearization accuracy assessment
% 4. Controller design for decoupled system
% 5. Decoupling approximation validation
%
% This sequence provides a complete characterization of the system
% from physical modeling through control design.
% =========================================================================

fprintf('\n');
fprintf('=========================================================================\n');
fprintf('MULTI-ZONE POWDER BED TEMPERATURE CONTROL ANALYSIS\n');
fprintf('=========================================================================\n');
fprintf('Starting comprehensive analysis...\n\n');

% STEP 1: Main temperature governing equation simulation
fprintf('STEP 1: Solving temperature governing equations...\n');
main_simulation();

% STEP 2: Geometric view factor analysis
fprintf('\nSTEP 2: Analyzing view factor relationships...\n');
analyze_view_factors();

% STEP 3: Linearization accuracy assessment
fprintf('\nSTEP 3: Evaluating linearization accuracy...\n');
analyze_linearization_accuracy();

% STEP 4: Decoupled controller design
fprintf('\nSTEP 4: Designing decoupled controllers...\n');
design_decoupled_controllers();

% STEP 5: Decoupling approximation validation
fprintf('\nSTEP 5: Validating decoupling assumptions...\n');
analyze_decoupling_approximation();

fprintf('\n');
fprintf('=========================================================================\n');
fprintf('ANALYSIS COMPLETE\n');
fprintf('=========================================================================\n');
fprintf('All results have been generated and saved.\n');
fprintf('Check the figures and command window output for detailed analysis.\n');
fprintf('Saved data file: decoupled_temperature_results.mat\n');
fprintf('=========================================================================\n');
