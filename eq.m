% =========================================================================
% TEMPERATURE CALCULATION FOR 9 ZONES (A1-A9)
% =========================================================================
% 
% This script calculates temperature Ti(t) for 9 different zones using the formula:
% Ti(t) = (((xi*t) + 592270.09) / ((22.151*t) + 1754.99)) - 273
%
% Where xi values are different for each zone A1 through A9
%
% Date: July 16, 2025
% =========================================================================

function eq()
    % Clear workspace and command window
    clear; clc; close all;
    
    %% =====================================================================
    %% PARAMETERS DEFINITION
    %% =====================================================================
    
    % Xi values for each zone (A1 through A9)
    xi = [8066.01, 8127.156, 8067.5724, 8141.8872, 8187.636, ...
          8141.8872, 8067.5724, 8127.156, 8067.5724];
    
    % Zone labels
    zone_labels = {'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9'};
    
    % Constants in the temperature formula
    a = 592270.09;   % Numerator constant
    b = 22.151;      % Denominator coefficient for t
    c = 1754.99;     % Denominator constant
    d = 273;         % Temperature offset (Kelvin to Celsius conversion)
    
    % Time range (seconds)
    t_start = 1;     % Start time (sec)
    t_end = 170;     % End time (sec) - based on your CSV data
    t_step = 1;      % Time step (sec)
    t = t_start:t_step:t_end;  % Time vector
    
    %% =====================================================================
    %% TEMPERATURE CALCULATIONS
    %% =====================================================================
    
    fprintf('=== TEMPERATURE CALCULATION FOR 9 ZONES ===\n');
    fprintf('Formula: Ti(t) = (((xi*t) + %.2f) / ((%.3f*t) + %.2f)) - %.0f\n\n', a, b, c, d);
    
    % Initialize temperature matrix
    % Rows: time points, Columns: zones (A1-A9)
    T = zeros(length(t), length(xi));
    
    % Calculate temperature for each zone
    for i = 1:length(xi)
        % Apply the temperature formula for zone i
        T(:,i) = ((xi(i) * t + a) ./ (b * t + c)) - d;
        
        % Display xi value for current zone
        fprintf('Zone %s: xi = %.4f\n', zone_labels{i}, xi(i));
    end
    
    %% =====================================================================
    %% RESULTS DISPLAY
    %% =====================================================================
    
    fprintf('\n=== SAMPLE TEMPERATURE VALUES ===\n');
    fprintf('Time(s)\t');
    for i = 1:length(zone_labels)
        fprintf('%s(°C)\t', zone_labels{i});
    end
    fprintf('\n');
    
    % Display first 10 time points
    for j = 1:min(10, length(t))
        fprintf('%.0f\t', t(j));
        for i = 1:length(xi)
            fprintf('%.2f\t', T(j,i));
        end
        fprintf('\n');
    end
    
    if length(t) > 10
        fprintf('...\t...\t...\t...\t...\t...\t...\t...\t...\t...\n');
        % Display last few time points
        for j = max(1, length(t)-2):length(t)
            fprintf('%.0f\t', t(j));
            for i = 1:length(xi)
                fprintf('%.2f\t', T(j,i));
            end
            fprintf('\n');
        end
    end
    
    %% =====================================================================
    %% VISUALIZATION
    %% =====================================================================
    
    % Create comprehensive plots
    create_temperature_plots(t, T, zone_labels, xi);
    
    %% =====================================================================
    %% STATISTICAL ANALYSIS
    %% =====================================================================
    
    analyze_temperature_statistics(t, T, zone_labels);
    
    %% =====================================================================
    %% DATA EXPORT
    %% =====================================================================
    
    % Export results to CSV file
    export_results_to_csv(t, T, zone_labels);
    
    fprintf('\n=== CALCULATION COMPLETE ===\n');
    fprintf('Results exported to: temperature_results.csv\n');
    fprintf('Plots generated for analysis\n');
end

function create_temperature_plots(t, T, zone_labels, xi)
    % =====================================================================
    % CREATE COMPREHENSIVE TEMPERATURE VISUALIZATION
    % =====================================================================
    
    % Create main figure with subplots
    figure('Position', [100, 100, 1400, 1000], 'Name', 'Temperature Analysis for 9 Zones');
    
    % PLOT 1: All temperature curves
    subplot(2, 3, 1);
    hold on;
    colors = lines(9);  % Generate 9 different colors
    
    for i = 1:9
        plot(t, T(:,i), 'Color', colors(i,:), 'LineWidth', 2, 'DisplayName', zone_labels{i});
    end
    
    xlabel('Time (seconds)');
    ylabel('Temperature (°C)');
    title('Temperature Evolution for All Zones');
    legend('Location', 'best', 'NumColumns', 3);
    grid on;
    
    % PLOT 2: Temperature differences from A5 (highest xi)
    subplot(2, 3, 2);
    reference_zone = 5;  % A5 has highest xi value
    hold on;
    
    for i = 1:9
        if i ~= reference_zone
            temp_diff = T(:,i) - T(:,reference_zone);
            plot(t, temp_diff, 'Color', colors(i,:), 'LineWidth', 2, 'DisplayName', sprintf('%s - A5', zone_labels{i}));
        end
    end
    
    xlabel('Time (seconds)');
    ylabel('Temperature Difference (°C)');
    title('Temperature Differences from A5 (Reference)');
    legend('Location', 'best', 'NumColumns', 2);
    grid on;
    
    % PLOT 3: Xi values bar chart
    subplot(2, 3, 3);
    bar(xi, 'FaceColor', [0.2, 0.6, 0.8]);
    xlabel('Zone');
    ylabel('Xi Value');
    title('Xi Values for Each Zone');
    set(gca, 'XTickLabel', zone_labels);
    grid on;
    
    % Add value labels on bars
    for i = 1:length(xi)
        text(i, xi(i) + 10, sprintf('%.1f', xi(i)), 'HorizontalAlignment', 'center');
    end
    
    % PLOT 4: Final temperatures
    subplot(2, 3, 4);
    final_temps = T(end, :);
    bar(final_temps, 'FaceColor', [0.8, 0.4, 0.2]);
    xlabel('Zone');
    ylabel('Final Temperature (°C)');
    title(sprintf('Final Temperatures at t = %.0f sec', t(end)));
    set(gca, 'XTickLabel', zone_labels);
    grid on;
    
    % Add value labels on bars
    for i = 1:length(final_temps)
        text(i, final_temps(i) + 0.5, sprintf('%.1f', final_temps(i)), 'HorizontalAlignment', 'center');
    end
    
    % PLOT 5: Temperature range over time
    subplot(2, 3, 5);
    temp_min = min(T, [], 2);
    temp_max = max(T, [], 2);
    temp_range = temp_max - temp_min;
    
    plot(t, temp_range, 'r-', 'LineWidth', 2);
    xlabel('Time (seconds)');
    ylabel('Temperature Range (°C)');
    title('Temperature Range Across All Zones');
    grid on;
    
    % PLOT 6: 3D surface plot of all zones
    subplot(2, 3, 6);
    [T_mesh, Zone_mesh] = meshgrid(1:9, t);
    surf(Zone_mesh, T_mesh, T');
    xlabel('Zone');
    ylabel('Time (seconds)');
    zlabel('Temperature (°C)');
    title('3D Temperature Surface');
    colorbar;
    view(45, 30);
    
    % Set zone labels
    set(gca, 'XTick', 1:9, 'XTickLabel', zone_labels);
end

function analyze_temperature_statistics(t, T, zone_labels)
    % =====================================================================
    % STATISTICAL ANALYSIS OF TEMPERATURE DATA
    % =====================================================================
    
    fprintf('\n=== STATISTICAL ANALYSIS ===\n');
    
    % Calculate statistics for each zone
    temp_stats = struct();
    
    for i = 1:9
        temp_stats.zone{i} = zone_labels{i};
        temp_stats.initial(i) = T(1, i);
        temp_stats.final(i) = T(end, i);
        temp_stats.max(i) = max(T(:, i));
        temp_stats.min(i) = min(T(:, i));
        temp_stats.mean(i) = mean(T(:, i));
        temp_stats.std(i) = std(T(:, i));
        temp_stats.range(i) = temp_stats.max(i) - temp_stats.min(i);
    end
    
    % Display statistics table
    fprintf('\nZone\tInitial\tFinal\tMax\tMin\tMean\tStd\tRange\n');
    fprintf('    \t(°C)\t(°C)\t(°C)\t(°C)\t(°C)\t(°C)\t(°C)\n');
    fprintf('----\t-------\t------\t----\t----\t----\t----\t-----\n');
    
    for i = 1:9
        fprintf('%s\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\n', ...
            temp_stats.zone{i}, temp_stats.initial(i), temp_stats.final(i), ...
            temp_stats.max(i), temp_stats.min(i), temp_stats.mean(i), ...
            temp_stats.std(i), temp_stats.range(i));
    end
    
    % Overall statistics
    fprintf('\n=== OVERALL STATISTICS ===\n');
    fprintf('Maximum temperature across all zones: %.2f °C\n', max(temp_stats.max));
    fprintf('Minimum temperature across all zones: %.2f °C\n', min(temp_stats.min));
    fprintf('Average temperature across all zones: %.2f °C\n', mean(temp_stats.mean));
    fprintf('Temperature variation between zones: %.2f °C\n', max(temp_stats.max) - min(temp_stats.min));
    
    % Find zones with extreme values
    [~, hottest_zone] = max(temp_stats.final);
    [~, coolest_zone] = min(temp_stats.final);
    
    fprintf('\nHottest zone at final time: %s (%.2f °C)\n', zone_labels{hottest_zone}, temp_stats.final(hottest_zone));
    fprintf('Coolest zone at final time: %s (%.2f °C)\n', zone_labels{coolest_zone}, temp_stats.final(coolest_zone));
end

function export_results_to_csv(t, T, zone_labels)
    % =====================================================================
    % EXPORT RESULTS TO CSV FILE
    % =====================================================================
    
    % Create header
    header = ['Time(sec)'];
    for i = 1:length(zone_labels)
        header = [header, sprintf(',%s(DegC)', zone_labels{i})];
    end
    
    % Create filename with timestamp
    filename = 'temperature_results.csv';
    
    % Write to file
    fid = fopen(filename, 'w');
    fprintf(fid, '%s\n', header);
    
    for j = 1:length(t)
        fprintf(fid, '%.0f', t(j));
        for i = 1:size(T, 2)
            fprintf(fid, ',%.6f', T(j, i));
        end
        fprintf(fid, '\n');
    end
    
    fclose(fid);
    
    fprintf('\nData exported to: %s\n', filename);
    fprintf('Format: Time(sec), A1(°C), A2(°C), ..., A9(°C)\n');
end

% =========================================================================
% MAIN EXECUTION
% =========================================================================
% Execute the main function when script is run
fprintf('=========================================================================\n');
fprintf('TEMPERATURE CALCULATION FOR 9 ZONES\n');
fprintf('=========================================================================\n');
fprintf('Starting calculation...\n\n');

eq();

fprintf('\n=========================================================================\n');
fprintf('CALCULATION COMPLETE\n');
fprintf('=========================================================================\n');
